"""
tests.test_fetchers
~~~~~~~~~~~~~~~~~~~~~
Test the LaTeX-On-HTTP file fetchers.

:copyright: (c) 2019 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

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


def test_resource_fetch_file_ssrf_blocked_disallowed_scheme(latex_on_http_api_url):
    r = requests.post(
        latex_on_http_api_url + "/builds/sync",
        json={"resources": [{"url": "file:///etc/passwd"}]},
    )
    assert r.status_code == 400
    response_payload = r.json()
    assert response_payload["error"] == "RESOURCE_FETCH_FAILURE"
    assert response_payload["fetch_error"]["type"] == "ssrf_blocked"
    assert response_payload["fetch_error"]["reason"] == "disallowed_scheme"


# TODO Check error for invalid base64/file resource.
