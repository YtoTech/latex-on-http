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
    r = requests.post(latex_on_http_api_url + "/builds/sync", json={
        "resources": [
            {
                "file": "https://raw.githubusercontent.com/facebook/thefacebook/master/presentation.tex"
            }
        ],
    })
    assert r.status_code == 400
    assert r.json() == {
        "error": "RESOURCE_FETCH_FAILURE",
        "fetch_error": {
            "http_code": 404,
        },
        "resource": {
            "file": "https://raw.githubusercontent.com/facebook/thefacebook/master/presentation.tex"
        },
    }

def test_resource_fetch_file_403(latex_on_http_api_url):
    r = requests.post(latex_on_http_api_url + "/builds/sync", json={
        "resources": [
            {
                "file": "https://httpbin.org/status/403"
            }
        ],
    })
    assert r.status_code == 400
    assert r.json() == {
        "error": "RESOURCE_FETCH_FAILURE",
        "fetch_error": {
            "http_code": 403,
        },
        "resource": {
            "file": "https://httpbin.org/status/403"
        },
    }

# TODO Test of file fetchers
# URL fetch mode:
# - proper error handling and message for HTTP errors (404, 403, 500, etc.)
# See https://github.com/YtoTech/latex-on-http/issues/6
