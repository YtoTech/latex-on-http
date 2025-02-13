# -*- coding: utf-8 -*-
"""
    tests.test_api_multipart
    ~~~~~~~~~~~~~~~~~~~~~
    Check Latex multipart compiling API.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import requests
from .utils.pdf import snapshot_pdf

LATEX_HELLO_WORLD = (
    "\\documentclass{article}\n\\begin{document}\nHello World\n\\end{document}"
)
SAMPLE_HELLO_WORLD = "hello_world"
LATEX_HELLO_WORLD_WITH_IMAGE = "\\documentclass{article}\n \\usepackage{graphicx}\n \\begin{document}\n Hello World\n \\includegraphics[height=2cm,width=7cm,keepaspectratio=true]{logo.png}\n \\end{document}"
SAMPLE_IMAGE_CONTENT = requests.get(
    "https://www.ytotech.com/images/ytotech_logo.png"
).content


def test_multipart_api_full_spec_simple(latex_on_http_api_url):
    """
    Compile a simple Latex document with multipart API by passing a complete resources
    specification and specifying the compiler.
    """
    # Create a multipart request.
    files = {"file1": ("hello_world.tex", LATEX_HELLO_WORLD)}
    form = {
        "compiler": "lualatex",
        "resources": '[{"main": "true", "multipart": "file1"}]',
    }
    r = requests.post(latex_on_http_api_url + "/builds/sync", files=files, data=form)
    # import pprint

    # pprint.pprint(r.json())
    assert r.status_code == 201
    snapshot_pdf(r.content, f"{SAMPLE_HELLO_WORLD}-multipart")


def test_multipart_api_full_spec_image(latex_on_http_api_url):
    """
    Compile a Latex document containing another image resource with multipart API
    by passing a complete resources specification and specifying the compiler.
    """
    # Create a multipart request.
    files = {"file1": ("hello_world.tex", LATEX_HELLO_WORLD_WITH_IMAGE)}
    form = {
        "compiler": "pdflatex",
        "resources": '[{"main": "true", "multipart": "file1"}, { "path": "logo.png", "url": "https://www.ytotech.com/images/ytotech_logo.png" }]',
    }
    r = requests.post(latex_on_http_api_url + "/builds/sync", files=files, data=form)
    assert r.status_code == 201


def test_multipart_api_inferred_compiler(latex_on_http_api_url):
    """
    Compile a Latex document with multipart API by passing a resources
    specification but without specifying the compiler.
    """
    # Create a multipart request.
    files = {"file1": ("hello_world.tex", LATEX_HELLO_WORLD)}
    form = {
        "resources": '[{"main": "true", "multipart": "file1"}]',
    }
    r = requests.post(latex_on_http_api_url + "/builds/sync", files=files, data=form)
    assert r.status_code == 201


# Error cases.


def test_multipart_api_invalid_json_resources_spec(latex_on_http_api_url):
    """
    Handle invalid json resources spec error.
    """
    # Create a multipart request.
    files = {"file1": ("hello_world.tex", LATEX_HELLO_WORLD)}
    form = {
        "resources": '[}}{"main": "true", "multipart": "file1"}]',
    }
    r = requests.post(latex_on_http_api_url + "/builds/sync", files=files, data=form)
    assert r.status_code == 400
    response_payload = r.json()
    assert response_payload["error"] == "INVALID_RESOURCES_JSON"


# Inferred / reconstructed resources specification.


def test_multipart_api_only_one_latex_file(latex_on_http_api_url):
    """
    Compile a Latex document with multipart API by passing only a Latex file.
    """
    # Create a multipart request.
    files = {"file1": ("hello_world.tex", LATEX_HELLO_WORLD)}
    r = requests.post(latex_on_http_api_url + "/builds/sync", files=files)
    assert r.status_code == 201


def test_multipart_api_only_one_unamed_latex_file(latex_on_http_api_url):
    """
    Compile a Latex document with multipart API by passing a Latex file that have not the .tex extension.
    """
    # Create a multipart request.
    files = {"file1": ("hello_world", LATEX_HELLO_WORLD)}
    r = requests.post(latex_on_http_api_url + "/builds/sync", files=files)
    assert r.status_code == 201


def test_multipart_api_latex_file_plus_image(latex_on_http_api_url):
    """
    Compile a Latex document with multipart API by passing only a Latex file.
    """
    # Create a multipart request.
    files = {
        "file1": ("hello_world.tex", LATEX_HELLO_WORLD_WITH_IMAGE),
        "file2": ("logo.png", SAMPLE_IMAGE_CONTENT),
    }
    r = requests.post(latex_on_http_api_url + "/builds/sync", files=files)
    assert r.status_code == 201
