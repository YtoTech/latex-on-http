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
import os

SAMPLE_DIR = os.getcwd() + '/tests/samples/'

COMPIL_HELLO_WORLD = {
    'resources': [
        {
            'content': '\\documentclass{article}\n\\begin{document}\nHello World\n\\end{document}'
        }
    ]
}
PDF_HELLO_WORLD = SAMPLE_DIR + 'hello_world.pdf'

def compareToSample(r, samplePath):
    with open(PDF_HELLO_WORLD, 'rb') as f:
        sample = f.read()
        assert len(r.content) == len(sample)
        # Generated binary PDF files differs.
        # TODO Use https://github.com/euske/pdfminer to compare?
        # assert generated == sample
        # Or read as string (utf-8) and compare N first charachers.
        # We may also find at which offset(s) the content differ between
        # compilation and compare all but that.

def test_api_index_redirect(latex_on_http_api_url):
    r = requests.get(latex_on_http_api_url, allow_redirects=False)
    assert r.status_code == 302
    assert r.headers['location'] == 'https://github.com/YtoTech/latex-on-http'

def test_simple_compilation_body(latex_on_http_api_url):
    r = requests.post(
        latex_on_http_api_url + '/compilers/latex', json=COMPIL_HELLO_WORLD
    )
    assert r.status_code == 201
    compareToSample(r, PDF_HELLO_WORLD)

# TODO API ping

# with open('hello_world.pdf', 'wb') as f:
#     f.write(r.content)

# TODO We can compile concurrently
# when one compilation is running the API still respond
# we can have at least 5 compilations at the same time
