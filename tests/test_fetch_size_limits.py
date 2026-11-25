"""
tests.test_fetch_size_limits
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for the fetched resource size limits (no network, no Docker).

:copyright: (c) 2026 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

import base64

from latexonhttp.resources import fetching
from latexonhttp.resources.fetching import fetch_resources


def _string_resource(content, path="__main_document__.tex"):
    return {
        "type": "utf8/string",
        "is_main_document": True,
        "build_path": path,
        "output_path": None,
        "body_source": {"raw_string": content},
    }


def _base64_resource(data, path="data.bin"):
    return {
        "type": "base64/file",
        "is_main_document": False,
        "build_path": path,
        "output_path": None,
        "body_source": {"raw_base64": base64.b64encode(data).decode("ascii")},
    }


def _cache_resource(path="cached.bin"):
    return {
        "type": "hash/cache",
        "is_main_document": False,
        "build_path": path,
        "output_path": None,
        "body_source": {"hash": "sha256:00000000000000000000000000000000"},
    }


# --- Individual limit (MAX_RESOURCE_SIZE) -----------------------------------


def test_individual_resource_over_limit_is_rejected(monkeypatch):
    monkeypatch.setattr(fetching, "MAX_RESOURCE_SIZE", 100)
    monkeypatch.setattr(fetching, "MAX_TOTAL_RESOURCE_SIZE", 0)
    fetched = []
    error = fetch_resources(
        [_string_resource("x" * 101)],
        lambda resource, data: fetched.append(resource["build_path"]),
    )
    assert error["error"] == "RESOURCE_FETCH_FAILURE"
    assert error["fetch_error"]["type"] == "resource_too_large"
    assert error["fetch_error"]["size"] == 101
    assert error["fetch_error"]["max_size"] == 100
    assert error["resource"]["build_path"] == "__main_document__.tex"
    # Rejected before on_fetched: never persisted.
    assert fetched == []


def test_individual_resource_at_limit_is_allowed(monkeypatch):
    monkeypatch.setattr(fetching, "MAX_RESOURCE_SIZE", 100)
    monkeypatch.setattr(fetching, "MAX_TOTAL_RESOURCE_SIZE", 0)
    fetched = []
    error = fetch_resources(
        [_string_resource("x" * 100)],
        lambda resource, data: fetched.append(resource["build_path"]),
    )
    assert error is None
    assert fetched == ["__main_document__.tex"]


def test_base64_resource_counts_toward_individual_limit(monkeypatch):
    monkeypatch.setattr(fetching, "MAX_RESOURCE_SIZE", 100)
    monkeypatch.setattr(fetching, "MAX_TOTAL_RESOURCE_SIZE", 0)
    error = fetch_resources(
        [_base64_resource(b"y" * 101)],
        lambda resource, data: None,
    )
    assert error["error"] == "RESOURCE_FETCH_FAILURE"
    assert error["fetch_error"]["type"] == "resource_too_large"
    assert error["fetch_error"]["size"] == 101


def test_cache_resource_counts_toward_individual_limit(monkeypatch):
    monkeypatch.setattr(fetching, "MAX_RESOURCE_SIZE", 100)
    monkeypatch.setattr(fetching, "MAX_TOTAL_RESOURCE_SIZE", 0)
    error = fetch_resources(
        [_cache_resource()],
        lambda resource, data: None,
        get_from_cache=lambda resource: (True, b"z" * 120),
    )
    assert error["error"] == "RESOURCE_FETCH_FAILURE"
    assert error["fetch_error"]["type"] == "resource_too_large"
    assert error["fetch_error"]["size"] == 120


def test_zero_individual_limit_disables_it(monkeypatch):
    monkeypatch.setattr(fetching, "MAX_RESOURCE_SIZE", 0)
    monkeypatch.setattr(fetching, "MAX_TOTAL_RESOURCE_SIZE", 0)
    fetched = []
    error = fetch_resources(
        [_string_resource("x" * 10_000)],
        lambda resource, data: fetched.append(resource["build_path"]),
    )
    assert error is None
    assert fetched == ["__main_document__.tex"]


# --- Combined limit (MAX_TOTAL_RESOURCE_SIZE) -------------------------------


def test_combined_resources_over_limit_is_rejected(monkeypatch):
    monkeypatch.setattr(fetching, "MAX_RESOURCE_SIZE", 1000)
    monkeypatch.setattr(fetching, "MAX_TOTAL_RESOURCE_SIZE", 1500)
    fetched = []
    resources = [
        _string_resource("a" * 800, path="__main_document__.tex"),
        _string_resource("b" * 800, path="second.tex"),
    ]
    error = fetch_resources(
        resources, lambda resource, data: fetched.append(resource["build_path"])
    )
    assert error["error"] == "RESOURCE_FETCH_FAILURE"
    assert error["fetch_error"]["type"] == "total_too_large"
    assert error["fetch_error"]["total_size"] == 1600
    assert error["fetch_error"]["max_total_size"] == 1500
    # The offending resource is the one that tipped the total over.
    assert error["resource"]["build_path"] == "second.tex"
    # The first resource passed both checks and was persisted.
    assert fetched == ["__main_document__.tex"]


def test_combined_resources_at_limit_is_allowed(monkeypatch):
    monkeypatch.setattr(fetching, "MAX_RESOURCE_SIZE", 1000)
    monkeypatch.setattr(fetching, "MAX_TOTAL_RESOURCE_SIZE", 1600)
    fetched = []
    resources = [
        _string_resource("a" * 800, path="__main_document__.tex"),
        _string_resource("b" * 800, path="second.tex"),
    ]
    error = fetch_resources(
        resources, lambda resource, data: fetched.append(resource["build_path"])
    )
    assert error is None
    assert fetched == ["__main_document__.tex", "second.tex"]


def test_zero_combined_limit_disables_it(monkeypatch):
    monkeypatch.setattr(fetching, "MAX_RESOURCE_SIZE", 0)
    monkeypatch.setattr(fetching, "MAX_TOTAL_RESOURCE_SIZE", 0)
    fetched = []
    resources = [
        _string_resource("a" * 10_000, path="__main_document__.tex"),
        _string_resource("b" * 10_000, path="second.tex"),
    ]
    error = fetch_resources(
        resources, lambda resource, data: fetched.append(resource["build_path"])
    )
    assert error is None
    assert fetched == ["__main_document__.tex", "second.tex"]


def test_combined_limit_fails_before_individual_one_does(monkeypatch):
    # One resource of 1600 bytes: individual limit (2000) passes, combined
    # limit (1500) fails -> total_too_large, not resource_too_large.
    monkeypatch.setattr(fetching, "MAX_RESOURCE_SIZE", 2000)
    monkeypatch.setattr(fetching, "MAX_TOTAL_RESOURCE_SIZE", 1500)
    error = fetch_resources(
        [_string_resource("x" * 1600)],
        lambda resource, data: None,
    )
    assert error["fetch_error"]["type"] == "total_too_large"
    assert error["fetch_error"]["total_size"] == 1600


def test_fetch_error_still_wins_over_size_limits(monkeypatch):
    # A fetch failure (invalid base64) is returned as-is, untouched by the
    # size limits.
    monkeypatch.setattr(fetching, "MAX_RESOURCE_SIZE", 100)
    monkeypatch.setattr(fetching, "MAX_TOTAL_RESOURCE_SIZE", 0)
    resource = {
        "type": "base64/file",
        "build_path": "data.bin",
        "body_source": {"raw_base64": "not base64!"},
    }
    error = fetch_resources([resource], lambda r, d: None)
    assert error["fetch_error"]["type"] == "invalid_base64"


# --- Defaults ----------------------------------------------------------------


def test_defaults_are_50mib_and_500mib():
    # The code defaults, not the runtime constants: the docker-compose test
    # stack pins MAX_RESOURCE_SIZE / MAX_TOTAL_RESOURCE_SIZE to 512 KiB (see
    # docker-compose.test.yml), so when the suite runs inside that stack the
    # runtime constants reflect the environment, not the defaults.
    assert fetching.DEFAULT_MAX_RESOURCE_SIZE == 50 * 1024 * 1024
    assert fetching.DEFAULT_MAX_TOTAL_RESOURCE_SIZE == 500 * 1024 * 1024
