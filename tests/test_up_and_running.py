# -*- coding: utf-8 -*-
"""
    tests.up_and_running
    ~~~~~~~~~~~~~~~~~~~~~
    Ensures the service is running and test basic functions.

    :copyright: (c) 2017 Yoan Tournade.
    :license: MIT, see LICENSE for more details.
"""
import pytest
import requests

def test_api_index(latex_on_http_api_url):
    r = requests.get(latex_on_http_api_url, allow_redirects=False)
    assert r.status_code == 302

def test_simple_compilation_body(latex_on_http_api_url):
    print(latex_on_http_api_url)
    assert 42 == 42

# TODO API ping

# TODO We can compile a simple document /compilers/latex

# TODO We can compile concurrently
# when one compilation is running the API still respond
# we can have at least 5 compilations at the same time
