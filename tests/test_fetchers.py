"""
tests.test_fetchers
~~~~~~~~~~~~~~~~~~~~~
Test the LaTeX-On-HTTP file fetchers.

:copyright: (c) 2019 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

import base64
import os

import pytest
import requests


def test_resource_fetch_file_404(latex_on_http_api_url):
    r = requests.post(
        latex_on_http_api_url + "/builds/sync",
        json={
            "resources": [
                {
                    "url": "https://raw.githubusercontent.com/facebook/thefacebook/master/presentation.tex"
                }
            ],
        },
    )
    assert r.status_code == 400
    response_payload = r.json()
    assert response_payload["error"] == "RESOURCE_FETCH_FAILURE"
    assert response_payload["fetch_error"]["http_code"] == 404
    assert response_payload["fetch_error"]["type"] == "http_error"
    assert (
        response_payload["resource"]["body_source"]["url"]
        == "https://raw.githubusercontent.com/facebook/thefacebook/master/presentation.tex"
    )


def test_resource_fetch_file_403(latex_on_http_api_url):
    r = requests.post(
        latex_on_http_api_url + "/builds/sync",
        json={
            "resources": [{"url": "https://httpbin.org/status/403"}],
        },
    )
    assert r.status_code == 400
    response_payload = r.json()
    print(response_payload)
    assert response_payload["error"] == "RESOURCE_FETCH_FAILURE"
    assert response_payload["fetch_error"]["http_code"] == 403
    assert response_payload["fetch_error"]["type"] == "http_error"
    assert (
        response_payload["resource"]["body_source"]["url"]
        == "https://httpbin.org/status/403"
    )


def test_resource_fetch_file_500(latex_on_http_api_url):
    r = requests.post(
        latex_on_http_api_url + "/builds/sync",
        json={
            "resources": [{"url": "https://httpbin.org/status/500"}],
        },
    )
    assert r.status_code == 400
    response_payload = r.json()
    print(response_payload)
    assert response_payload["error"] == "RESOURCE_FETCH_FAILURE"
    assert response_payload["fetch_error"]["http_code"] == 500
    assert response_payload["fetch_error"]["type"] == "http_error"
    assert (
        response_payload["resource"]["body_source"]["url"]
        == "https://httpbin.org/status/500"
    )


def test_resource_fetch_file_timeout(latex_on_http_api_url):
    # ; The fetch timeout is configurable by environment and reduced in the
    # ; test configuration (docker-compose.test.yml) so that this test runs
    # ; quickly. With the default timeout (60s) the delayed response would
    # ; arrive in time and the test could not exercise the timeout case.
    if float(os.getenv("FETCHER_HTTP_REQ_READ_TIMEOUT", 60)) >= 10:
        pytest.skip(
            "FETCHER_HTTP_REQ_READ_TIMEOUT must be set below 10 seconds"
            " (in the app container) to test the timeout fetcher"
        )
    r = requests.post(
        latex_on_http_api_url + "/builds/sync",
        json={
            "resources": [{"url": "https://httpbin.org/delay/10"}],
        },
    )
    assert r.status_code == 400
    response_payload = r.json()
    assert response_payload["error"] == "RESOURCE_FETCH_FAILURE"
    assert response_payload["fetch_error"]["type"] == "request_timeout"
    assert response_payload["fetch_error"]["http_code"] is None
    assert (
        response_payload["resource"]["body_source"]["url"]
        == "https://httpbin.org/delay/10"
    )


def test_resource_fetch_file_name_resolution_failure(latex_on_http_api_url):
    r = requests.post(
        latex_on_http_api_url + "/builds/sync",
        json={
            "resources": [
                {"url": "https://doesnotexist-cucumber-impossible.org/willnotresolve"}
            ],
        },
    )
    assert r.status_code == 400
    response_payload = r.json()
    assert response_payload["error"] == "RESOURCE_FETCH_FAILURE"
    assert response_payload["fetch_error"]["http_code"] == None
    assert (
        response_payload["resource"]["body_source"]["url"]
        == "https://doesnotexist-cucumber-impossible.org/willnotresolve"
    )


# --- SSRF guard: user-supplied URLs must not reach internal addresses ------


@pytest.mark.parametrize(
    "url, reason",
    [
        ("http://127.0.0.1/secret", "loopback"),
        ("http://169.254.169.254/latest/meta-data/", "link_local"),
        ("http://10.0.0.1/internal", "private_ip"),
        ("http://192.168.0.10/", "private_ip"),
        ("http://[::1]/", "loopback"),
    ],
)
def test_resource_fetch_file_ssrf_blocked(latex_on_http_api_url, url, reason):
    r = requests.post(
        latex_on_http_api_url + "/builds/sync",
        json={"resources": [{"url": url}]},
    )
    assert r.status_code == 400
    response_payload = r.json()
    assert response_payload["error"] == "RESOURCE_FETCH_FAILURE"
    assert response_payload["fetch_error"]["type"] == "ssrf_blocked"
    assert response_payload["fetch_error"]["reason"] == reason
    assert response_payload["fetch_error"]["http_code"] is None
    assert response_payload["resource"]["body_source"]["url"] == url


def test_resource_fetch_file_invalid_url_unsupported_scheme(latex_on_http_api_url):
    # A non-http(s) scheme is unfetchable, so it is an invalid_url that names the
    # allowed schemes, not an ssrf block.
    r = requests.post(
        latex_on_http_api_url + "/builds/sync",
        json={"resources": [{"url": "file:///etc/passwd"}]},
    )
    assert r.status_code == 400
    response_payload = r.json()
    assert response_payload["error"] == "RESOURCE_FETCH_FAILURE"
    assert response_payload["fetch_error"]["type"] == "invalid_url"
    assert response_payload["fetch_error"]["reason"] == "unsupported_scheme"
    assert response_payload["fetch_error"]["allowed_schemes"] == ["http", "https"]
    assert response_payload["fetch_error"]["http_code"] is None


def test_resource_fetch_file_invalid_url_missing_scheme(latex_on_http_api_url):
    # A schemeless URL is a client error (400 invalid_url), never a 500.
    r = requests.post(
        latex_on_http_api_url + "/builds/sync",
        json={"resources": [{"url": "/raw/example.com/main.tex"}]},
    )
    assert r.status_code == 400
    response_payload = r.json()
    assert response_payload["error"] == "RESOURCE_FETCH_FAILURE"
    assert response_payload["fetch_error"]["type"] == "invalid_url"
    assert response_payload["fetch_error"]["reason"] == "no_scheme"
    assert response_payload["fetch_error"]["allowed_schemes"] == ["http", "https"]


# --- Fetched resource size limits --------------------------------------------
# ; The test configuration caps fetched resources at 512 KiB (MAX_RESOURCE_SIZE
# ; and MAX_TOTAL_RESOURCE_SIZE, see docker-compose.test.yml) while the request
# ; body stays under its 1 MiB limit (MAX_REQUEST_BODY_BYTES), so the base64
# ; payloads below exceed the resource limits without tripping the 413.


def test_resource_fetch_individual_size_limit(latex_on_http_api_url):
    # A 600 KiB base64 resource exceeds the 512 KiB per-resource limit.
    payload = {
        "resources": [
            {
                "main": True,
                "file": base64.b64encode(b"x" * (600 * 1024)).decode("ascii"),
            }
        ]
    }
    r = requests.post(latex_on_http_api_url + "/builds/sync", json=payload)
    assert r.status_code == 400
    response_payload = r.json()
    assert response_payload["error"] == "RESOURCE_FETCH_FAILURE"
    assert response_payload["fetch_error"]["type"] == "resource_too_large"
    assert response_payload["fetch_error"]["size"] == 600 * 1024
    assert response_payload["fetch_error"]["max_size"] == 512 * 1024


def test_resource_fetch_combined_size_limit(latex_on_http_api_url):
    # Two 300 KiB resources under the individual limit, but 600 KiB combined,
    # over the 512 KiB combined limit.
    one_file = base64.b64encode(b"x" * (300 * 1024)).decode("ascii")
    payload = {
        "resources": [
            {"main": True, "file": one_file},
            {"path": "data.bin", "file": one_file},
        ]
    }
    r = requests.post(latex_on_http_api_url + "/builds/sync", json=payload)
    assert r.status_code == 400
    response_payload = r.json()
    assert response_payload["error"] == "RESOURCE_FETCH_FAILURE"
    assert response_payload["fetch_error"]["type"] == "total_too_large"
    assert response_payload["fetch_error"]["total_size"] == 600 * 1024
    assert response_payload["fetch_error"]["max_total_size"] == 512 * 1024
    # The offending resource is the one that tipped the combined total over.
    assert response_payload["resource"]["build_path"] == "data.bin"


def test_resource_fetch_url_individual_size_limit(latex_on_http_api_url):
    # A 700 KiB remote file exceeds the 512 KiB per-resource limit; the URL
    # fetcher streams its body and aborts at the cap (max_size + 1 bytes read).
    r = requests.post(
        latex_on_http_api_url + "/builds/sync",
        json={"resources": [{"url": "https://httpbin.org/bytes/716800"}]},
    )
    assert r.status_code == 400
    response_payload = r.json()
    assert response_payload["error"] == "RESOURCE_FETCH_FAILURE"
    assert response_payload["fetch_error"]["type"] == "resource_too_large"
    assert response_payload["fetch_error"]["size"] == 512 * 1024 + 1
    assert response_payload["fetch_error"]["max_size"] == 512 * 1024


# TODO Check error for invalid base64/file resource.
