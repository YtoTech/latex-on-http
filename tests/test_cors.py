# -*- coding: utf-8 -*-
"""
    tests.test_cors
    ~~~~~~~~~~~~~~~~~~~~~
    Ensures the API endpoints are accessible from cross-origin requests.

    :copyright: (c) 2020 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import pytest
import requests


def test_cors_cross_origin(latex_on_http_api_url):
    """
    The build endpoint is accessible from cross-origin requests.
    """
    r = requests.request("OPTIONS", latex_on_http_api_url + "/builds/sync")
    assert r.status_code == 200
    assert sorted(r.headers["Allow"].split(", ")) == ["GET", "HEAD", "OPTIONS", "POST"]
    assert r.headers["Access-Control-Allow-Origin"] == "*"
