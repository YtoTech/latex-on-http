# -*- coding: utf-8 -*-
"""
    tests.test_up_and_running
    ~~~~~~~~~~~~~~~~~~~~~
    Ensures the service is running and test basic functions.

    :copyright: (c) 2017-2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import pytest
import requests
from latexonhttp.utils.misc import get_api_version


def test_api_index(latex_on_http_api_url):
    """
    The API index gives some metadata on itself.
    """
    r = requests.get(latex_on_http_api_url, allow_redirects=False)
    assert r.status_code == 200
    assert r.json() == {
        "message": "Welcome to the Latex-On-HTTP API",
        "source": "https://github.com/YtoTech/latex-on-http",
        "documentation": "https://github.com/YtoTech/latex-on-http",
        "version": get_api_version(),
    }


# TODO proper ping API?

# TODO Test of file fetchers
# URL fetch mode:
# - proper error handling and message for HTTP errors (404, 403, 500, etc.)
# See https://github.com/YtoTech/latex-on-http/issues/6
