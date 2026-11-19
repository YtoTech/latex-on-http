"""
tests.conftest
~~~~~~~~~~~~~~~~~~~~~
Fixtures for tests.

:copyright: (c) 2017-2018 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

import os

import pytest


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

    # ; Integration tests are skipped when no app URL is configured,
    # ; so that unit-tier runs (e.g. in agent/LLM containers without
    # ; Docker/LaTeX) stay green instead of failing on connection errors.
    app_url = os.getenv("LATEX_ON_HTTP_API_URL")
    if not app_url:
        pytest.skip(
            "LATEX_ON_HTTP_API_URL is not configured;"
            " this integration test needs a running app"
            " (make test-docker-compose or a local instance)"
        )
    yield app_url
