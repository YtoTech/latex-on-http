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
    # TODO Here we could run a docker container of the app.
    # Advantage:
    # * sure we're testing target integration env;
    # * no need to install Latex on the host machine to run tests;
    # * we can wait for the command to finish before starting the test.
    # TODO In most tests, we do not really need to restart a new webserver instance.
    # Only tests that make the server crash will imply a restart, but this actually
    # should not possible.
    # Of course we will have to ensure the webserver has finished executing
    # the current test requests before allowing to pass to the next one.
    # Even in this case, no much state should be shared in webserver if
    # we have concurrent requrests.
    appProcess = subprocess.Popen(['make', 'start'])
    # appProcess = subprocess.Popen(['make', 'debug'])
    time.sleep(0.5)
    yield 'http://localhost:8080/'
    print("teardown latex_on_http_api")
    appProcess.terminate()
    print("teardowned")
