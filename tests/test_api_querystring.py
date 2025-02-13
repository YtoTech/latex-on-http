# -*- coding: utf-8 -*-
"""
    tests.test_api_querystring
    ~~~~~~~~~~~~~~~~~~~~~
    Check Latex GET/querystring compiling API.

    :copyright: (c) 2020 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import pprint
import requests
from .utils.pdf import snapshot_pdf

LATEX_HELLO_WORLD = (
    "\\documentclass{article}\n\\begin{document}\nHello World\n\\end{document}"
)
SAMPLE_HELLO_WORLD = "hello_world"

COMPIL_UPLATEX_JAPANESE = "% !TEX uplatex\n\\documentclass[uplatex]{jsarticle}\n\n\\title{up\\LaTeX\\ 実験}\n\\author{林蓮枝}\n\n\\begin{document}\n\n\\maketitle\n\n\\begin{abstract}\n本稿では、文書組版システムup\\LaTeX{}の使い方を解説します。\nup\\LaTeX{}を利用するときには、あらかじめ文章中に\\TeX{}コマンドと呼ばれる組版用の指示を混在させ\\ldots\n\\end{abstract}\n\n\\section{導入}\nこんにちは世界\n\n\\end{document}"
SAMPLE_HELLO_JAPANESE = "hello_japanese"

LATEX_HELLO_WORLD_WITH_IMAGE = "\\documentclass{article}\n \\usepackage{graphicx}\n \\begin{document}\n Hello World\n \\includegraphics[height=2cm,width=7cm,keepaspectratio=true]{logo.png}\n \\end{document}"
SAMPLE_IMAGE_CONTENT = requests.get(
    "https://www.ytotech.com/images/ytotech_logo.png"
).content

LATEX_MULTI_RESOURCES = "\\documentclass{article}\n \\usepackage{graphicx}\n  \\begin{document}\n Hello World\\\\\n \\includegraphics[height=2cm,width=7cm,keepaspectratio=true]{logo.png}\n \\include{page2}\n \\end{document}"
LATEX_MULTI_RESOURCES_PAGE2 = "VGhpcyBpcyB0aGUgc2Vjb25kIHBhZ2UsIHdoaWNoIHdhcyBwYXNzZWQgYXMgYSBiYXNlNjQgZW5jb2RlZCBmaWxl"


def test_querystring_hello_world(latex_on_http_api_url):
    """
    Compile a simple Latex document with querystring API by an encoded Latex document content.
    """
    # Create a query string request.
    r = requests.get(
        latex_on_http_api_url + "/builds/sync",
        params={"content": LATEX_HELLO_WORLD},
    )
    assert r.status_code == 201


def test_querystring_hello_world_compiler(latex_on_http_api_url):
    """
    Compile a simple Latex document with querystring API by an encoded Latex document content,
    and specifying the compiler.
    """
    # Create a query string request.
    r = requests.get(
        latex_on_http_api_url + "/builds/sync",
        params={"content": LATEX_HELLO_WORLD, "compiler": "lualatex"},
    )
    assert r.status_code == 201
    snapshot_pdf(r.content, f"{SAMPLE_HELLO_WORLD}-multipart")


def test_querystring_hello_japanese(latex_on_http_api_url):
    """
    Compile a japanese Latex document with querystring API by an encoded Latex document content,
    and specifying the compiler.
    """
    # Create a query string request.
    r = requests.get(
        latex_on_http_api_url + "/builds/sync",
        params={"content": COMPIL_UPLATEX_JAPANESE, "compiler": "uplatex"},
    )
    assert r.status_code == 201


# Add resources
# &resource-path[]=logo.png&resource-value[]=https://www.ytotech.com/images/ytotech_logo.png


def test_querystring_full_spec_image(latex_on_http_api_url):
    """
    Compile a Latex document containing another image resource with querystring API
    by passing a complete resources specification and specifying the compiler.
    """
    # Create a query string request.
    r = requests.get(
        latex_on_http_api_url + "/builds/sync",
        params={
            "content": LATEX_HELLO_WORLD_WITH_IMAGE,
            "compiler": "pdflatex",
            "resource-path[]": "logo.png",
            "resource-type[]": "url",
            "resource-value[]": "https://www.ytotech.com/images/ytotech_logo.png",
        },
    )
    # import pprint

    # pprint.pprint(r.json())
    assert r.status_code == 201


def test_querystring_multi_resources(latex_on_http_api_url):
    """
    Compile a Latex document containing multiple annex resources with querystring API,
    by passing a complete resources specification and specifying the compiler.
    """
    # Create a query string request.
    r = requests.get(
        latex_on_http_api_url + "/builds/sync",
        params={
            "content": LATEX_MULTI_RESOURCES,
            "compiler": "pdflatex",
            "resource-path[]": ["logo.png", "page2.tex"],
            "resource-type[]": ["url", "base64"],
            "resource-value[]": [
                "https://www.ytotech.com/images/ytotech_logo.png",
                LATEX_MULTI_RESOURCES_PAGE2,
            ],
        },
    )
    if r.status_code != 201:
        pprint.pprint(r.text)
        # pprint.pprint(r.json())
    assert r.status_code == 201


# TODO Specify output file name?
