# -*- coding: utf-8 -*-
"""
    tests.test_fetchers
    ~~~~~~~~~~~~~~~~~~~~~
    Test the Latex-on-HTTP file fetchers.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
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
    assert (
        response_payload["resource"]["body_source"]["url"]
        == "https://raw.githubusercontent.com/facebook/thefacebook/master/presentation.tex"
    )


def test_resource_fetch_file_403(latex_on_http_api_url):
    r = requests.post(
        latex_on_http_api_url + "/builds/sync",
        json={"resources": [{"url": "https://httpbin.org/status/403"}],},
    )
    assert r.status_code == 400
    response_payload = r.json()
    assert response_payload["error"] == "RESOURCE_FETCH_FAILURE"
    assert response_payload["fetch_error"]["http_code"] == 403
    assert (
        response_payload["resource"]["body_source"]["url"]
        == "https://httpbin.org/status/403"
    )


def test_resource_fetch_file_500(latex_on_http_api_url):
    r = requests.post(
        latex_on_http_api_url + "/builds/sync",
        json={"resources": [{"url": "https://httpbin.org/status/500"}],},
    )
    assert r.status_code == 400
    response_payload = r.json()
    assert response_payload["error"] == "RESOURCE_FETCH_FAILURE"
    assert response_payload["fetch_error"]["http_code"] == 500
    assert (
        response_payload["resource"]["body_source"]["url"]
        == "https://httpbin.org/status/500"
    )


# TODO Check error for invalid base64/file resource.
