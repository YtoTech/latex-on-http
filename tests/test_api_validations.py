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
from latexonhttp.sandbox import SandboxUnavailable
from latexonhttp.resources.fetching import (
    fetcher_base64_file,
    fetcher_url_file,
    fetcher_utf8_string,
)


def build_client():
    test_app = Flask(__name__)
    test_app.register_blueprint(builds_app, url_prefix="/builds")
    return test_app.test_client()


def test_sandbox_unavailable_returns_503_and_preserves_shell_escape_option(monkeypatch):
    received_options = []
    reported = []

    def fail_compilation(_compiler, _directory, _main, _workspace, options):
        received_options.append(options)
        raise SandboxUnavailable("bwrap: Operation not permitted")

    monkeypatch.setattr("latexonhttp.api.builds.latexToPdf", fail_compilation)
    monkeypatch.setattr(
        "latexonhttp.api.builds.forward_resource_to_cache",
        lambda _resource, _data: (True, None),
    )
    monkeypatch.setattr(
        "latexonhttp.api.builds.report_sandbox_diagnostic",
        lambda diagnostic, **context: reported.append((diagnostic, context)),
    )
    response = build_client().post(
        "/builds/sync",
        json={
            "compiler": "uplatex",
            "resources": [{"main": True, "content": "test"}],
            "options": {"compiler": {"shell_escape": True}},
        },
    )

    assert response.status_code == 503
    assert response.get_json() == {"error": "SANDBOX_UNAVAILABLE"}
    assert received_options[0]["compiler"]["shell_escape"] is True
    diagnostic, context = reported[0]
    assert diagnostic.kind == "permission_denied"
    assert diagnostic.binary == "bubblewrap"
    assert context["compiler"] == "uplatex"


def test_malformed_resource_is_rejected_before_build():
    response = build_client().post(
        "/builds/sync", json={"resources": ["not a resource mapping"]}
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "INVALID_PAYLOAD_SHAPE"


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


def test_object_content_returns_400_instead_of_server_error():
    content = {"unexpected": "object"}
    response = build_client().post(
        "/builds/sync",
        json={"resources": [{"main": True, "content": content}]},
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "INVALID_STRING_CONTENT"
    assert payload["message"] == "The resource content field must contain a string."
    assert payload["fetch_error"] == {
        "type": "invalid_content_type",
        "content_type": "dict",
    }
    assert payload["resource"]["body_source"]["raw_string"] == content


@pytest.mark.parametrize(
    ("content", "content_type"),
    [
        (None, "NoneType"),
        (42, "int"),
        (3.14, "float"),
        (True, "bool"),
        (["not", "a", "string"], "list"),
        ({"not": "a string"}, "dict"),
    ],
)
def test_non_string_content_is_rejected(content, content_type):
    data, error = fetcher_utf8_string(
        {"type": "utf8/string", "body_source": {"raw_string": content}},
        None,
    )

    assert data is None
    assert error["error"] == "INVALID_STRING_CONTENT"
    assert error["fetch_error"]["type"] == "invalid_content_type"
    assert error["fetch_error"]["content_type"] == content_type


def test_valid_string_content_is_still_encoded():
    data, error = fetcher_utf8_string(
        {"type": "utf8/string", "body_source": {"raw_string": "Hello \\LaTeX"}},
        None,
    )

    assert data == b"Hello \\LaTeX"
    assert error is None


def test_url_without_scheme_returns_400_instead_of_server_error():
    url = "/raw/YtoTech/latex-on-http/master/examples/templates/moderncv.tex"
    response = build_client().get("/builds/sync", query_string={"url": url})

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "RESOURCE_FETCH_FAILURE"
    assert payload["fetch_error"]["type"] == "invalid_url"
    assert "No scheme supplied" in payload["fetch_error"]["exception_content"]
    assert payload["fetch_error"]["http_code"] is None
    assert payload["fetch_error"]["http_response_content"] is None
    assert payload["resource"]["body_source"]["url"] == url


@pytest.mark.parametrize(
    "url",
    [
        "/raw/YtoTech/latex-on-http/master/examples/templates/moderncv.tex",
        "example.com/main.tex",
        "https://",
        "ftp://example.com/main.tex",
    ],
)
def test_malformed_or_unsupported_urls_are_rejected(url):
    data, error = fetcher_url_file(
        {"type": "url/file", "body_source": {"url": url}},
        None,
    )

    assert data is None
    assert error["error"] == "RESOURCE_FETCH_FAILURE"
    assert error["fetch_error"]["type"] == "invalid_url"
    assert error["fetch_error"]["exception_content"]
    assert error["fetch_error"]["http_code"] is None
