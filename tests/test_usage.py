"""Usage token scoring tests.

Unit tier: the scoring module is a pure function set over plain dicts
(no Flask, no store, no database), so the token model -- weights, KiB
normalization, cache discount, rounding, clock-skew clamp -- runs
without Docker, Valkey or LaTeX.
"""

from datetime import UTC, datetime, timedelta

import pytest

from latexonhttp import usage

RECEIVED_AT = datetime(2026, 11, 19, 12, 0, 0, tzinfo=UTC)

CATEGORIES = ("incoming", "fetch", "processing", "outgoing")


def scores(
    payload_size=0,
    fetched_size=0,
    cache_hits_size=0,
    replied_delta=0.0,
    outgoing_size=0,
):
    """Score one synthetic request, defaults mirroring an empty one."""
    fetched = {
        "fetched_resources_count": 0,
        "fetched_resources_size": fetched_size,
        "fetched_resources_cache_hits": 0,
        "fetched_resources_cache_hits_size": cache_hits_size,
    }
    return usage.usage_scores(
        usage.new_usage(RECEIVED_AT, payload_size),
        fetched,
        RECEIVED_AT + timedelta(seconds=replied_delta),
        outgoing_size,
    )


# -------------
# Configuration.
# -------------


def test_default_weights_charge_data_per_kib_and_time_per_second():
    assert usage.USAGE_WEIGHTS == {
        "incoming": 1.0,
        "fetch": 1.0,
        "cache": 0.0,
        "processing": 1.0,
        "outgoing": 1.0,
    }
    result = scores(
        payload_size=2048, fetched_size=1024, replied_delta=3.0, outgoing_size=4096
    )
    assert result == {
        "incoming": 2.0,
        "fetch": 1.0,
        "processing": 3.0,
        "outgoing": 4.0,
        "total": 10.0,
    }


def test_categories_are_rescaled_by_their_weights(monkeypatch):
    monkeypatch.setitem(usage.USAGE_WEIGHTS, "incoming", 2.0)
    monkeypatch.setitem(usage.USAGE_WEIGHTS, "outgoing", 0.5)
    result = scores(payload_size=1024, outgoing_size=2048)
    assert result["incoming"] == 2.0
    assert result["outgoing"] == 1.0


# -------------
# Usage record.
# -------------


def test_new_usage_records_admission_data():
    record = usage.new_usage(RECEIVED_AT, 123)
    assert record == {"received_at": RECEIVED_AT, "incoming_bytes": 123}


# -------------
# Categories.
# -------------


def test_processing_is_the_received_to_replied_wall_time():
    assert scores(replied_delta=7.5)["processing"] == pytest.approx(7.5)


def test_processing_is_clamped_when_the_clock_skews_backwards():
    assert scores(replied_delta=-60.0)["processing"] == 0.0


def test_fetched_effective_bytes_discounts_cache_hits(monkeypatch):
    fetched = {
        "fetched_resources_size": 5000,
        "fetched_resources_cache_hits_size": 1000,
    }
    # Cache hits free by default: only the network bytes are charged.
    assert usage.fetched_effective_bytes(fetched) == 4000
    monkeypatch.setitem(usage.USAGE_WEIGHTS, "cache", 0.25)
    assert usage.fetched_effective_bytes(fetched) == 4250


def test_cache_hits_are_free_in_the_fetch_component():
    result = scores(fetched_size=4096, cache_hits_size=4096)
    assert result["fetch"] == 0.0


def test_cache_hits_are_charged_at_the_configured_discount(monkeypatch):
    monkeypatch.setitem(usage.USAGE_WEIGHTS, "cache", 0.5)
    result = scores(fetched_size=4096, cache_hits_size=2048)
    # 2048 network bytes + 0.5 x 2048 cached bytes = 3072 bytes = 3 tokens.
    assert result["fetch"] == pytest.approx(3.0)


def test_a_request_without_resources_scores_only_the_payload():
    result = scores(payload_size=512)
    assert result == {
        "incoming": 0.5,
        "fetch": 0.0,
        "processing": 0.0,
        "outgoing": 0.0,
        "total": 0.5,
    }


# -------------
# Total.
# -------------


def test_components_are_rounded_and_sum_to_the_total():
    result = scores(
        payload_size=1000,
        fetched_size=1000,
        replied_delta=0.25,
        outgoing_size=1000,
    )
    components = [result[category] for category in CATEGORIES]
    # Every stored value fits the 6-decimal scale...
    for value in [*components, result["total"]]:
        assert value == round(value, 6)
    # ...and the stored components add up to the stored total.
    assert result["total"] == pytest.approx(sum(components), abs=1e-9)
