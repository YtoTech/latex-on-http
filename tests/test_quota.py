"""Quota and rate-limiting tests.

Unit tier: an in-memory fake Valkey store stands in for the real one
(monkeypatched over `latexonhttp.quota._get_client`), so the window counting,
escalation and failure-mode logic run without Docker, Valkey or LaTeX.
Integration tier (requires `LATEX_ON_HTTP_API_URL` + the
`docker-compose.quota-test.yml` override, see `make test-quota`): exercises
the HTTP behavior with low limits and spoofed `X-Forwarded-For` values.
"""

import time
import uuid
from datetime import UTC, datetime

import flask
import pytest
import requests

from latexonhttp import quota

APP = flask.Flask(__name__)


class FakeValkey:
    """Minimal in-memory Valkey: counters, TTLs and transactions."""

    def __init__(self, clock=0):
        self.clock = clock
        # key -> [value, expires_at, has_ttl]
        self.data = {}

    def advance(self, seconds):
        self.clock += seconds

    def _entry(self, key):
        entry = self.data.get(key)
        if entry is None:
            return None
        value, expires_at, _ = entry
        if expires_at is not None and expires_at <= self.clock:
            del self.data[key]
            return None
        return entry

    def get(self, key):
        entry = self._entry(key)
        return None if entry is None else entry[0]

    def set(self, key, value, ex=None):
        expires_at = None if ex is None else self.clock + ex
        self.data[key] = [str(value), expires_at, ex is not None]

    def incr(self, key):
        entry = self._entry(key)
        if entry is None:
            self.data[key] = ["1", None, False]
            return 1
        entry[0] = str(int(entry[0]) + 1)
        return int(entry[0])

    def decr(self, key):
        entry = self._entry(key)
        if entry is None:
            self.data[key] = ["-1", None, False]
            return -1
        entry[0] = str(int(entry[0]) - 1)
        return int(entry[0])

    def expire(self, key, seconds, nx=False):
        entry = self._entry(key)
        if entry is None:
            return False
        if nx and entry[2]:
            return False
        entry[1] = self.clock + seconds
        entry[2] = True
        return True

    def ttl(self, key):
        entry = self._entry(key)
        if entry is None:
            return -2
        if entry[1] is None:
            return -1
        return int(entry[1] - self.clock)

    def pipeline(self, transaction=True):
        return FakePipeline(self)


class FakePipeline:
    """Buffered transaction: commands apply in order on execute()."""

    def __init__(self, store):
        self.store = store
        self.ops = []

    def incr(self, key):
        self.ops.append(("incr", key))
        return self

    def decr(self, key):
        self.ops.append(("decr", key))
        return self

    def expire(self, key, seconds, nx=False):
        self.ops.append(("expire", key, seconds, nx))
        return self

    def get(self, key):
        self.ops.append(("get", key))
        return self

    def execute(self):
        handlers = {
            "incr": lambda op: self.store.incr(op[1]),
            "decr": lambda op: self.store.decr(op[1]),
            "expire": lambda op: self.store.expire(op[1], op[2], nx=op[3]),
            "get": lambda op: self.store.get(op[1]),
        }
        results = [handlers[op[0]](op) for op in self.ops]
        self.ops = []
        return results


class ExplodingStore:
    """A store that fails on every operation (outage simulation)."""

    def get(self, key):
        raise RuntimeError("store unavailable")


@pytest.fixture
def store(monkeypatch):
    fake = FakeValkey()
    monkeypatch.setattr(quota, "_get_client", lambda: fake)
    return fake


@pytest.fixture
def limits():
    original = dict(quota.QUOTA_LIMITS)
    yield quota.QUOTA_LIMITS
    quota.QUOTA_LIMITS.clear()
    quota.QUOTA_LIMITS.update(original)


# -------------
# Client IP extraction.
# -------------


def test_get_client_ip_prefers_first_forwarded_hop():
    with APP.test_request_context(
        "/", headers={"X-Forwarded-For": "203.0.113.7, 10.0.0.1"}
    ):
        assert quota.get_client_ip(flask.request) == "203.0.113.7"


def test_get_client_ip_falls_back_to_remote_addr():
    with APP.test_request_context("/", environ_base={"REMOTE_ADDR": "198.51.100.4"}):
        assert quota.get_client_ip(flask.request) == "198.51.100.4"


def test_get_client_ip_supports_a_custom_header(monkeypatch):
    monkeypatch.setattr(quota, "QUOTA_CLIENT_IP_HEADER", "CF-Connecting-IP")
    with APP.test_request_context(
        "/",
        headers={
            "CF-Connecting-IP": "203.0.113.9",
            "X-Forwarded-For": "203.0.113.8",
        },
    ):
        assert quota.get_client_ip(flask.request) == "203.0.113.9"


# -------------
# Window buckets.
# -------------


def test_window_bucket_alignment():
    epoch = int(datetime(2026, 11, 19, 13, 22, 26, tzinfo=UTC).timestamp())
    bucket, end = quota.window_bucket("second", epoch)
    assert bucket == str(epoch) and end == epoch + 1
    bucket, end = quota.window_bucket("minute", epoch)
    assert bucket == str(epoch // 60) and end == epoch - epoch % 60 + 60
    bucket, end = quota.window_bucket("hour", epoch)
    assert bucket == str(epoch // 3600) and end == epoch - epoch % 3600 + 3600
    bucket, end = quota.window_bucket("day", epoch)
    assert bucket == "20261119"
    assert datetime.fromtimestamp(end, tz=UTC) == datetime(2026, 11, 20, tzinfo=UTC)
    bucket, end = quota.window_bucket("week", epoch)
    assert bucket == "2026-W47"
    monday = datetime.fromtimestamp(end - 604800, tz=UTC)
    assert monday.weekday() == 0 and monday.hour == 0


def test_window_bucket_rejects_unknown_period():
    with pytest.raises(ValueError):
        quota.window_bucket("decade", 0)


# -------------
# Allowance / denial over the windows.
# -------------


def test_second_window_allows_limit_then_denies(store, limits):
    limits.update({"second": 2, "minute": 100, "hour": 100, "day": 100, "week": 100})
    epoch = 1763559600
    store.clock = epoch
    assert quota.check_quota("1.1.1.1", now=epoch)["allowed"]
    second = quota.check_quota("1.1.1.1", now=epoch)
    assert second["allowed"] and second["remaining"] == 0
    third = quota.check_quota("1.1.1.1", now=epoch)
    assert not third["allowed"]
    assert third["period"] == "second"
    assert third["banned"] is False
    assert 1 <= third["retry_after"] <= 2


def test_minute_window_caps_despite_idle_seconds(store, limits):
    limits.update({"second": 10, "minute": 3, "hour": 100, "day": 100, "week": 100})
    epoch = 1763559600
    store.clock = epoch
    for offset in range(3):
        assert quota.check_quota("1.1.1.1", now=epoch + offset)["allowed"]
    fourth = quota.check_quota("1.1.1.1", now=epoch + 3)
    assert not fourth["allowed"]
    assert fourth["period"] == "minute"


def test_denial_does_not_consume_quota(store, limits):
    limits.update({"second": 1, "minute": 2, "hour": 10, "day": 10, "week": 10})
    epoch = 1763559600
    store.clock = epoch
    assert quota.check_quota("1.1.1.1", now=epoch)["allowed"]
    assert not quota.check_quota("1.1.1.1", now=epoch)["allowed"]
    # Denied requests left the window counters untouched...
    minute_counter = quota._counter_key("1.1.1.1", "minute", epoch // 60)
    assert store.get(minute_counter) == "1"
    # ...and only the violation feed recorded the abuse.
    assert store.get("quota:viol:15m:1.1.1.1") == "1"
    # Once the window rolls over, the client can compile again.
    assert quota.check_quota("1.1.1.1", now=epoch + 61)["allowed"]


def test_day_and_week_windows_are_calendar_aligned(store, limits):
    limits.update({"second": 100, "minute": 100, "hour": 100, "day": 1, "week": 5})
    epoch = int(datetime(2026, 11, 19, 13, 22, 26, tzinfo=UTC).timestamp())
    store.clock = epoch
    assert quota.check_quota("1.1.1.1", now=epoch)["allowed"]
    denial = quota.check_quota("1.1.1.1", now=epoch)
    assert not denial["allowed"] and denial["period"] == "day"
    # Next UTC day: allowed again.
    next_day = int(datetime(2026, 11, 20, tzinfo=UTC).timestamp())
    assert quota.check_quota("1.1.1.1", now=next_day)["allowed"]


# -------------
# Escalation.
# -------------


def test_violations_escalate_to_short_ban(store, limits):
    limits.update({"second": 1, "minute": 1, "hour": 10, "day": 10, "week": 10})
    epoch = 1763559600
    store.clock = epoch
    decisions = [quota.check_quota("1.1.1.1", now=epoch) for _ in range(4)]
    assert decisions[0]["allowed"]
    # The two first denials are plain window breaches...
    assert not decisions[1]["banned"] and not decisions[2]["banned"]
    # ...the third violation triggers the short ban.
    assert decisions[3]["banned"] is True
    assert decisions[3]["retry_after"] == quota.QUOTA_BAN_SHORT_DURATION
    assert store.get("quota:ban:1.1.1.1") == "short"


def test_ban_rearms_while_hammering(store, limits):
    limits.update({"second": 1, "minute": 1, "hour": 10, "day": 10, "week": 10})
    epoch = 1763559600
    store.clock = epoch
    quota.check_quota("1.1.1.1", now=epoch)
    for _ in range(3):
        quota.check_quota("1.1.1.1", now=epoch)
    store.advance(1800)  # Halfway into the 1h ban.
    decision = quota.check_quota("1.1.1.1", now=int(store.clock))
    assert decision["banned"] is True
    # Hammering re-arms the ban to its full duration.
    assert store.ttl("quota:ban:1.1.1.1") == quota.QUOTA_BAN_SHORT_DURATION


def test_persistent_abuse_escalates_to_long_ban(store, limits):
    limits.update({"second": 1, "minute": 1, "hour": 100, "day": 100, "week": 100})
    epoch = 1763559600
    store.clock = epoch
    quota.check_quota("1.1.1.1", now=epoch)
    decision = None
    for _ in range(11):  # 24h-worth of violations (10) while hammering.
        decision = quota.check_quota("1.1.1.1", now=epoch)
    assert decision["banned"] is True
    assert decision["retry_after"] == quota.QUOTA_BAN_LONG_DURATION
    assert store.get("quota:ban:1.1.1.1") == "long"


def test_three_bans_within_a_day_escalate_to_long(store, limits):
    limits.update({"second": 1, "minute": 1, "hour": 100, "day": 100, "week": 100})
    epoch = 1763559600
    store.clock = epoch
    for episode in range(3):
        quota.check_quota("1.1.1.1", now=int(store.clock))
        for _ in range(3):
            quota.check_quota("1.1.1.1", now=int(store.clock))
        if episode < 2:
            assert store.get("quota:ban:1.1.1.1") == "short"
            # Ban (1h) and 15-min violation window expire between episodes.
            store.advance(
                quota.QUOTA_BAN_SHORT_DURATION + quota.QUOTA_VIOLATION_SHORT_WINDOW
            )
    assert store.get("quota:ban:1.1.1.1") == "long"


# -------------
# Inactivity, allowlist, failure modes.
# -------------


def test_ban_expires_after_inactivity(store, limits):
    limits.update({"second": 1, "minute": 1, "hour": 100, "day": 100, "week": 100})
    epoch = 1763559600
    store.clock = epoch
    quota.check_quota("1.1.1.1", now=epoch)
    for _ in range(3):
        quota.check_quota("1.1.1.1", now=epoch)
    assert store.get("quota:ban:1.1.1.1") == "short"
    store.advance(quota.QUOTA_BAN_SHORT_DURATION + 1)
    assert quota.check_quota("1.1.1.1", now=int(store.clock))["allowed"]


def test_disabled_without_store(monkeypatch):
    monkeypatch.setattr(quota, "_get_client", lambda: None)
    assert quota.check_quota("1.1.1.1") is None


def test_disabled_by_configuration(monkeypatch, store):
    monkeypatch.setattr(quota, "QUOTA_ENABLED", False)
    assert quota.check_quota("1.1.1.1", now=1000) is None
    assert not store.data  # Nothing was recorded.


def test_allowlisted_ip_bypasses_quota(store, monkeypatch, limits):
    monkeypatch.setattr(quota, "QUOTA_TRUSTED_IPS", {"203.0.113.9"})
    limits.update({"second": 1, "minute": 1, "hour": 1, "day": 1, "week": 1})
    assert quota.check_quota("203.0.113.9", now=1000) is None
    assert not store.data
    assert quota.check_quota("203.0.113.10", now=1000)["allowed"]


def test_fail_open_on_store_error(monkeypatch):
    monkeypatch.setattr(quota, "_get_client", lambda: ExplodingStore())
    assert quota.check_quota("1.1.1.1") is None


def test_fail_closed_returns_unavailable(monkeypatch):
    monkeypatch.setattr(quota, "QUOTA_FAIL_MODE", "closed")
    monkeypatch.setattr(quota, "_get_client", lambda: ExplodingStore())
    decision = quota.check_quota("1.1.1.1")
    assert decision["unavailable"] is True
    body, status, _ = quota.quota_rejection(decision)
    assert status == 503 and body["error"] == "QUOTA_STORE_UNAVAILABLE"


# -------------
# HTTP contract helpers.
# -------------


def test_rejection_response_shape():
    decision = quota._decision(
        allowed=False,
        period="hour",
        limit=40,
        remaining=0,
        reset=1763563200,
        retry_after=812,
        banned=False,
    )
    body, status, headers = quota.quota_rejection(decision)
    assert status == 429 and body["error"] == "QUOTA_EXCEEDED"
    assert body["quota"]["period"] == "hour"
    assert body["quota"]["limit"] == 40
    assert body["quota"]["banned"] is False
    assert headers["Retry-After"] == "812"
    assert headers["X-RateLimit-Limit"] == "40"
    assert headers["X-RateLimit-Remaining"] == "0"
    assert headers["X-RateLimit-Reset"] == "1763563200"


def test_rejection_response_shape_when_banned():
    decision = quota._decision(
        allowed=False,
        banned=True,
        ban_expires_at=1763646000,
        retry_after=82800,
    )
    body, status, headers = quota.quota_rejection(decision)
    assert status == 429
    assert body["quota"]["banned"] is True
    assert body["quota"]["period"] is None
    assert headers["Retry-After"] == "82800"
    assert "X-RateLimit-Limit" not in headers


def test_allowed_decision_has_no_retry_after():
    decision = quota._decision(
        allowed=True, period="minute", limit=6, remaining=4, reset=1000
    )
    headers = quota.rate_limit_headers(decision)
    assert headers["X-RateLimit-Remaining"] == "4"
    assert "Retry-After" not in headers


# -------------
# Integration tier (requires the app + the quota-test Compose override).
# -------------


def _flood(api_url, ip, count):
    headers = {"X-Forwarded-For": ip}
    return [
        requests.post(f"{api_url}/builds/sync", json={"resources": []}, headers=headers)
        for _ in range(count)
    ]


def test_integration_quota_denies_flood(latex_on_http_api_url):
    ip = f"203.0.113.{uuid.uuid4().int % 200 + 2}"
    responses = _flood(latex_on_http_api_url, ip, 10)
    statuses = [response.status_code for response in responses]
    assert 429 in statuses
    first_denial = responses[statuses.index(429)]
    assert first_denial.json()["error"] == "QUOTA_EXCEEDED"
    assert int(first_denial.headers["Retry-After"]) >= 1
    assert "X-RateLimit-Limit" in first_denial.headers
    assert all(status != 429 for status in statuses[: statuses.index(429)])


def test_integration_quota_bans_repeated_abuse(latex_on_http_api_url):
    ip = f"203.0.114.{uuid.uuid4().int % 200 + 2}"
    responses = _flood(latex_on_http_api_url, ip, 15)
    denial = responses[-1]
    assert denial.status_code == 429
    assert denial.json()["quota"]["banned"] is True
    # A ban (1h) rather than a one-minute window.
    assert int(denial.headers["Retry-After"]) > 60


def test_integration_quota_exposes_headers_on_allowed(latex_on_http_api_url):
    ip = f"203.0.115.{uuid.uuid4().int % 200 + 2}"
    response = requests.post(
        f"{latex_on_http_api_url}/builds/sync",
        json={"resources": []},
        headers={"X-Forwarded-For": ip},
    )
    # The invalid payload is rejected (counted at admission) but allowed.
    assert response.status_code == 400
    assert int(response.headers["X-RateLimit-Limit"]) >= 1
    assert int(response.headers["X-RateLimit-Remaining"]) >= 0
    assert int(response.headers["X-RateLimit-Reset"]) > int(time.time())
