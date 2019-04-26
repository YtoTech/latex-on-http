# -*- coding: utf-8 -*-
"""
    tests.up_and_running
    ~~~~~~~~~~~~~~~~~~~~~
    Ensures the service is running and test basic functions.

    :copyright: (c) 2017-2018 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import pytest
import requests
from concurrent.futures import ThreadPoolExecutor
from latexonhttp.utils.misc import get_api_version
from requests_futures.sessions import FuturesSession
from .utils.pdf import snapshot_pdf

COMPIL_HELLO_WORLD = {
    "compiler": "lualatex",
    "resources": [
        {
            "content": "\\documentclass{article}\n\\begin{document}\nHello World\n\\end{document}"
        }
    ],
}
SAMPLE_HELLO_WORLD = "hello_world"


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


def test_simple_compilation_body(latex_on_http_api_url):
    """
    Compile a simple Latex document, text-only, passed directly in document
    definition content entry.
    """
    r = requests.post(latex_on_http_api_url + "/builds/sync", json=COMPIL_HELLO_WORLD)
    assert r.status_code == 201
    snapshot_pdf(r.content, SAMPLE_HELLO_WORLD)


def test_concurrent_compilations(latex_on_http_api_url):
    """
    We can launch multiple compilation jobs concurrently.
    
    TODO: This concurrent test is too instable in CI.
    How to ensure in a different way that the compilation requests
    are treated in concurrently and not sequentially?
    Check that the response times are not sequentials? (Or with a reduced delta?)
    """
    concurrentSessions = 10
    session = FuturesSession(
        executor=ThreadPoolExecutor(max_workers=concurrentSessions)
    )
    requestsList = []
    # Spam all requests concurrently.
    for i in range(0, concurrentSessions):
        requestsList.append(
            session.post(
                latex_on_http_api_url + "/builds/sync", json=COMPIL_HELLO_WORLD
            )
        )
    # Check the API ping during load.
    r = requests.get(latex_on_http_api_url, allow_redirects=False, timeout=4)
    assert r.status_code == 200
    # Check all results.
    for requestFuture in requestsList:
        r = requestFuture.result()
        assert r.status_code == 201
        print(r.elapsed.total_seconds())
        snapshot_pdf(r.content, SAMPLE_HELLO_WORLD)


# TODO proper ping API?
