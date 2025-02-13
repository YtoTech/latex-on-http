# -*- coding: utf-8 -*-
"""
    tests.test_compiling
    ~~~~~~~~~~~~~~~~~~~~~
    Check Latex compiling results.

    :copyright: (c) 2017-2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import requests
from concurrent.futures import ThreadPoolExecutor
from requests_futures.sessions import FuturesSession
from .utils.pdf import snapshot_pdf

COMPIL_HELLO_WORLD = {
    "compiler": "pdflatex",
    "resources": [
        {
            "content": "\\documentclass{article}\n\\begin{document}\nHello World\n\\end{document}"
        }
    ],
}
SAMPLE_HELLO_WORLD = "hello_world"

COMPIL_UPLATEX_JAPANESE = {
    "compiler": "uplatex",
    "resources": [
        {
            "content": "% !TEX uplatex\n\\documentclass[uplatex]{jsarticle}\n\n\\title{up\\LaTeX\\ 実験}\n\\author{林蓮枝}\n\n\\begin{document}\n\n\\maketitle\n\n\\begin{abstract}\n本稿では、文書組版システムup\\LaTeX{}の使い方を解説します。\nup\\LaTeX{}を利用するときには、あらかじめ文章中に\\TeX{}コマンドと呼ばれる組版用の指示を混在させ\\ldots\n\\end{abstract}\n\n\\section{導入}\nこんにちは世界\n\n\\end{document}"
        }
    ],
}
SAMPLE_HELLO_JAPANESE = "hello_japanese"

COMPIL_HELLO_CONTEXT = {
    "compiler": "context",
    "resources": [{"content": "\\starttext\nHello world.\n\\stoptext"}],
}
SAMPLE_HELLO_CONTEXT = "hello_context"


def test_no_payload_error(latex_on_http_api_url):
    r = requests.post(latex_on_http_api_url + "/builds/sync", json={})
    assert r.status_code == 400
    assert r.json() == {
        "error": "MISSING_COMPILATION_SPECIFICATION",
    }


def test_simple_compilation_body_pdflatex(latex_on_http_api_url):
    """
    Compile a simple Latex document, text-only, passed directly in document
    definition content entry.
    """
    r = requests.post(latex_on_http_api_url + "/builds/sync", json=COMPIL_HELLO_WORLD)
    assert r.status_code == 201
    # snapshot_pdf(r.content, f"{SAMPLE_HELLO_WORLD}-pdflatex")


def test_simple_compilation_body_xelatex(latex_on_http_api_url):
    """
    Compile a simple Latex document, text-only, passed directly in document
    definition content entry.
    """
    r = requests.post(
        latex_on_http_api_url + "/builds/sync",
        json={
            **COMPIL_HELLO_WORLD,
            "compiler": "xelatex",
        },
    )
    assert r.status_code == 201
    # snapshot_pdf(r.content, f"{SAMPLE_HELLO_WORLD}-xelatex")


def test_simple_compilation_body_lualatex(latex_on_http_api_url):
    """
    Compile a simple Latex document, text-only, passed directly in document
    definition content entry.
    """
    r = requests.post(
        latex_on_http_api_url + "/builds/sync",
        json={
            **COMPIL_HELLO_WORLD,
            "compiler": "lualatex",
        },
    )
    assert r.status_code == 201
    snapshot_pdf(r.content, f"{SAMPLE_HELLO_WORLD}-lualatex")


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
                latex_on_http_api_url + "/builds/sync",
                json={
                    **COMPIL_HELLO_WORLD,
                    "compiler": "lualatex",
                },
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
        snapshot_pdf(r.content, f"{SAMPLE_HELLO_WORLD}-concurrent")


def test_uplatex_compiler_japanese(latex_on_http_api_url):
    """
    Compile a japanese Latex document, text-only, passed directly in document
    definition content entry, with uplatex.
    """
    r = requests.post(
        latex_on_http_api_url + "/builds/sync", json=COMPIL_UPLATEX_JAPANESE
    )
    # import pprint

    # pprint.pprint(r.json())
    assert r.status_code == 201
    # snapshot_pdf(r.content, SAMPLE_HELLO_JAPANESE)


def test_context_compiler_hello(latex_on_http_api_url):
    """
    Compile a minimal Context document, text-only, passed directly in document
    definition content entry.
    """
    r = requests.post(latex_on_http_api_url + "/builds/sync", json=COMPIL_HELLO_CONTEXT)
    assert r.status_code == 201
    # snapshot_pdf(r.content, SAMPLE_HELLO_CONTEXT)
