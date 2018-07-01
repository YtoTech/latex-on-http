# -*- coding: utf-8 -*-
"""
    tests.conftest
    ~~~~~~~~~~~~~~~~~~~~~
    Fixtures for tests.

    :copyright: (c) 2017-2018 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import pytest
import subprocess
import time


@pytest.fixture(scope="function")
def latex_on_http_api_url():
    # Here we expect a running docker container of the app.
    # Pros:
    # * sure we're testing target integration env;
    # * no need to install Latex on the host machine to run tests;
    # * we can wait for the command to finish before starting the tests.

    # It is launched externally, so we can still run tests
    # on the host or any configuration.

    # To let Docker takes care of itself, simply use:
    # make test-docker-compose

    # TODO Make the port configurable.
    # Use an env variable.
    yield "http://localhost:9898"
