"""
tests.test_api_validation
~~~~~~~~~~~~~~~~~~~~~~~~~
Check malformed resource inputs return useful client errors.

:copyright: (c) 2026 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

import base64
import threading

import pytest
from flask import Flask

from latexonhttp.api.builds import builds_app, validate_input_spec
from latexonhttp.docs import docs_app
from latexonhttp.resources.fetching import (
    fetcher_base64_file,
    fetcher_url_file,
    fetcher_utf8_string,
)
from latexonhttp.sandbox import SandboxUnavailable


@pytest.fixture(autouse=True)
def disable_job_tracking(monkeypatch):
    monkeypatch.setattr("latexonhttp.api.builds.create_job", lambda _metadata: None)
    monkeypatch.setattr(
        "latexonhttp.api.builds.update_job", lambda *_args, **_kwargs: None
    )


def build_client():
    test_app = Flask(__name__)
    test_app.register_blueprint(builds_app, url_prefix="/builds")
    # Registered (like in the real app) so error responses can build their
    # /docs/ documentation links via url_for.
    test_app.register_blueprint(docs_app)
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


@pytest.mark.parametrize("include_log_files", [True, False])
def test_generated_file_error_returns_400(monkeypatch, include_log_files):
    compilation_output = {
        "status": "error",
        "error": {
            "error": "GENERATED_FILE_READ_ERROR",
            "file_read_error": {
                "reason": "too_large",
                "path": "main.pdf",
            },
        },
        "pdf": None,
        "log_files": {"main.log": "LaTeX log"},
        "output_path": "main.pdf",
        "duration": 1.236,
        "logs": "compiler diagnostics",
        "commands": ["latexmk", "main.tex"],
        "is_timeout": False,
    }
    monkeypatch.setattr(
        "latexonhttp.api.builds.latexToPdf", lambda *args, **kwargs: compilation_output
    )
    monkeypatch.setattr(
        "latexonhttp.api.builds.forward_resource_to_cache",
        lambda _resource, _data: (True, None),
    )

    response = build_client().post(
        "/builds/sync",
        json={
            "resources": [{"main": True, "content": "test"}],
            "options": {
                "response": {"log_files_on_failure": include_log_files},
            },
        },
    )

    assert response.status_code == 400
    expected = {
        "error": "GENERATED_FILE_READ_ERROR",
        "file_read_error": {
            "reason": "too_large",
            "path": "main.pdf",
        },
        "duration": 1.24,
        "logs": "compiler diagnostics",
    }
    if include_log_files:
        expected["log_files"] = {"main.log": "LaTeX log"}
    assert response.get_json() == expected


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
    # A schemeless URL is unusable, so it is an invalid_url (a client error,
    # 400 -- never a 500), not an ssrf block; it names the reason and the
    # schemes this service accepts.
    assert payload["fetch_error"]["type"] == "invalid_url"
    assert payload["fetch_error"]["reason"] == "no_scheme"
    assert payload["fetch_error"]["allowed_schemes"] == ["http", "https"]
    assert payload["fetch_error"]["http_code"] is None
    assert payload["resource"]["body_source"]["url"] == url


@pytest.mark.parametrize(
    ("url", "reason", "with_allowed_schemes"),
    [
        (
            "/raw/YtoTech/latex-on-http/master/examples/templates/moderncv.tex",
            "no_scheme",
            True,
        ),
        ("example.com/main.tex", "no_scheme", True),
        ("https://", "missing_host", False),
        ("ftp://example.com/main.tex", "unsupported_scheme", True),
    ],
)
def test_malformed_or_unsupported_urls_are_rejected(url, reason, with_allowed_schemes):
    data, error = fetcher_url_file(
        {"type": "url/file", "body_source": {"url": url}},
        None,
    )

    assert data is None
    assert error["error"] == "RESOURCE_FETCH_FAILURE"
    # Unusable URLs are invalid_url (not ssrf_blocked): no scheme -> no_scheme,
    # a non-http(s) scheme -> unsupported_scheme, no host -> missing_host.
    assert error["fetch_error"]["type"] == "invalid_url"
    assert error["fetch_error"]["reason"] == reason
    assert error["fetch_error"]["detail"]
    assert error["fetch_error"]["http_code"] is None
    if with_allowed_schemes:
        assert error["fetch_error"]["allowed_schemes"] == ["http", "https"]
    else:
        assert "allowed_schemes" not in error["fetch_error"]


def test_naked_get_returns_missing_compilation_specification():
    """A browser navigating to /builds/sync with no parameters gets a 400.

    Regression test for GlitchTip #11969: such a request used to reach the
    shape validator with ``{"resources": []}`` and crash with a 500.
    """
    response = build_client().get("/builds/sync")

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "MISSING_COMPILATION_SPECIFICATION"
    # A browser landing here is told where the request format is documented.
    assert body["documentation"].endswith("/docs/api/builds-sync/")


def test_empty_resources_returns_missing_compilation_specification():
    response = build_client().post("/builds/sync", json={"resources": []})

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "MISSING_COMPILATION_SPECIFICATION"
    assert body["documentation"].endswith("/docs/api/builds-sync/")


VALID_SPEC = {
    "compiler": "lualatex",
    "resources": [{"content": "Hello world", "main": True}],
}
INVALID_SPEC_INVALID_COMPILER = {
    "compiler": "badtex",
    "resources": [{"content": "Hello world", "main": True}],
}
INVALID_SPEC_INVALID_RESOURCES = {"resources": "not a list"}


def test_validate_input_spec_is_thread_safe():
    """Concurrent validation calls must not share state (GlitchTip #11969).

    cerberus.Validator instances are stateful, so every call must use its
    own: with a shared instance, concurrent calls clobber each other's
    document, schema and rules queue (wrong results, IndexError).
    """
    cases = [
        (VALID_SPEC, False),
        (INVALID_SPEC_INVALID_COMPILER, True),
        (INVALID_SPEC_INVALID_RESOURCES, True),
    ]
    lock = threading.Lock()
    failures = []

    def worker(spec, expected_has_errors):
        try:
            for _ in range(200):
                validator = validate_input_spec(spec)
                if bool(validator.errors) != expected_has_errors:
                    with lock:
                        failures.append((spec, validator.errors))
        except Exception as exc:
            with lock:
                failures.append(exc)

    threads = [
        threading.Thread(target=worker, args=case) for case in cases for _ in range(3)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert failures == []
