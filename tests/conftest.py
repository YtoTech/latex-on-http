# -*- coding: utf-8 -*-
"""
    tests.conftest
    ~~~~~~~~~~~~~~~~~~~~~
    Fixtures for tests.

    :copyright: (c) 2017 Yoan Tournade.
    :license: MIT, see LICENSE for more details.
"""
import pytest
import subprocess
import time

@pytest.fixture(scope="function")
def latex_on_http_api_url():
    appProcess = subprocess.Popen(['make', 'start'])
    time.sleep(1)
    yield 'http://localhost:8080/'
    print("teardown latex_on_http_api")
    appProcess.terminate()
    print("teardowned")
