# -*- coding: utf-8 -*-
"""
tests.test_api_validation
~~~~~~~~~~~~~~~~~~~~~~~~~
Check malformed resource inputs return useful client errors.

:copyright: (c) 2026 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

import base64

import pytest
from flask import Flask

from latexonhttp.api.builds import builds_app
from latexonhttp.resources.fetching import fetcher_base64_file


def build_client():
    test_app = Flask(__name__)
    test_app.register_blueprint(builds_app, url_prefix="/builds")
    return test_app.test_client()


def test_resource_rejects_multiple_source_fields():
    response = build_client().post(
        "/builds/sync",
        json={
            "compiler": "pdflatex",
            "resources": [
                {
                    "main": True,
                    "path": "main.tex",
                    "file": "main.tex",
                    "content": (
                        "\\documentclass{article}\\begin{document}Hi\\end{document}"
                    ),
                }
            ],
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "MULTIPLE_RESOURCE_SOURCES",
        "message": (
            "Use only one source field per resource: "
            "url, file, git, tar, cache or content."
        ),
        "resource_index": 0,
        "source_fields": ["file", "content"],
    }


def test_invalid_base64_returns_400_instead_of_server_error():
    response = build_client().post(
        "/builds/sync",
        json={"resources": [{"main": True, "file": "main.tex"}]},
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "INVALID_BASE64_CONTENT"
    assert payload["message"] == (
        "The resource file field must contain valid Base64-encoded content."
    )
    assert payload["fetch_error"]["type"] == "invalid_base64"
    assert payload["fetch_error"]["exception_content"]
    assert payload["resource"]["body_source"]["raw_base64"] == "main.tex"


@pytest.mark.parametrize(
    "raw_base64", ["not base64!", "%%%%", "\N{LATIN SMALL LETTER E WITH ACUTE}"]
)
def test_invalid_base64_alphabet_is_rejected(raw_base64):
    data, error = fetcher_base64_file(
        {"type": "base64/file", "body_source": {"raw_base64": raw_base64}},
        None,
    )

    assert data is None
    assert error["error"] == "INVALID_BASE64_CONTENT"
    assert error["fetch_error"]["type"] == "invalid_base64"


def test_valid_base64_is_still_decoded():
    raw_base64 = base64.b64encode(b"hello").decode("ascii")

    data, error = fetcher_base64_file(
        {"type": "base64/file", "body_source": {"raw_base64": raw_base64}},
        None,
    )

    assert data == b"hello"
    assert error is None
