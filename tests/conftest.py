# -*- coding: utf-8 -*-
"""
    tests.conftest
    ~~~~~~~~~~~~~~~~~~~~~
    Fixtures for tests.

    :copyright: (c) 2017 Yoan Tournade.
    :license: MIT, see LICENSE for more details.
"""
import pytest

@pytest.fixture(scope="function")
def latex_on_http_api_url():
    return 'http://localhost:8080/'
    # TODO How to teardown? Yielf?
