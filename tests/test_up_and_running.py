# -*- coding: utf-8 -*-
"""
    tests.up_and_running
    ~~~~~~~~~~~~~~~~~~~~~
    Ensures the service is running and test basic functions.

    :copyright: (c) 2017 Yoan Tournade.
    :license: MIT, see LICENSE for more details.
"""
import pytest

def test_simple_compilation_body(latex_on_http_api_url):
    print(latex_on_http_api_url)
    assert 42 == 41

# TODO API ping

# TODO We can compile a simple document /compilers/latex

# TODO We can compile concurrently
# when one compilation is running the API still respond
# we can have at least 5 compilations at the same time
