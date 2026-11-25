"""
tests.test_content_disposition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Check the Content-Disposition header returned with the PDF output.

The output filename echoes back the uploaded document name and may contain
non-ASCII characters (RFC 9110 requires printable ASCII header values): an
invalid header would make gunicorn reject the whole response (InvalidHeader)
after a successful compilation.

:copyright: (c) 2026 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

import io

import pytest
from flask import Flask
from werkzeug.http import parse_options_header

from latexonhttp.api.builds import build_content_disposition_header, builds_app

PDF_OUTPUT = {
    "status": "ok",
    "error": None,
    "pdf": b"%PDF-1.7 fake pdf",
    "log_files": {},
    "duration": 1.0,
    "logs": "",
    "commands": [],
    "is_timeout": False,
}


@pytest.fixture(autouse=True)
def disable_job_tracking(monkeypatch):
    monkeypatch.setattr("latexonhttp.api.builds.create_job", lambda _metadata: None)
    monkeypatch.setattr(
        "latexonhttp.api.builds.update_job", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "latexonhttp.api.builds.forward_resource_to_cache",
        lambda _resource, _data: (True, None),
    )


def build_client():
    test_app = Flask(__name__)
    test_app.register_blueprint(builds_app, url_prefix="/builds")
    return test_app.test_client()


def test_header_for_simple_ascii_output_path():
    assert build_content_disposition_header("main.pdf") == 'inline; filename="main.pdf"'


def test_header_uses_basename_only():
    assert (
        build_content_disposition_header("sub/dir/main.pdf")
        == 'inline; filename="main.pdf"'
    )


def test_header_for_spaces_in_filename():
    assert (
        build_content_disposition_header("hello world.pdf")
        == 'inline; filename="hello world.pdf"'
    )


def test_header_escapes_quotes_and_backslashes():
    assert (
        build_content_disposition_header('weird"name.pdf')
        == 'inline; filename="weird\\"name.pdf"'
    )
    assert (
        build_content_disposition_header("back\\slash.pdf")
        == 'inline; filename="back\\\\slash.pdf"'
    )


def test_header_replaces_control_characters():
    assert (
        build_content_disposition_header("bad\nname.pdf")
        == 'inline; filename="bad_name.pdf"'
    )


def test_header_for_missing_output_path():
    assert build_content_disposition_header(None) == 'inline; filename="output.pdf"'
    assert build_content_disposition_header("") == 'inline; filename="output.pdf"'


def test_header_percent_encodes_non_ascii_filename():
    # Regression: an uploaded "Lab02-肖奕然.tex" used to produce
    # "inline;filename=Lab02-肖奕然.pdf", rejected by gunicorn with
    # InvalidHeader — after the compilation succeeded.
    expected = (
        'inline; filename="Lab02-%E8%82%96%E5%A5%95%E7%84%B6.pdf"; '
        "filename*=UTF-8''Lab02-%E8%82%96%E5%A5%95%E7%84%B6.pdf"
    )
    assert build_content_disposition_header("Lab02-肖奕然.pdf") == expected


def test_header_decodes_back_to_the_output_filename():
    for output_path in ["main.pdf", "Lab02-肖奕然.pdf", "héllo wörld.pdf"]:
        disposition = build_content_disposition_header(output_path)
        _, options = parse_options_header(disposition)
        assert options["filename"] == output_path


def test_sync_response_header_is_ascii_safe_for_unicode_filename(monkeypatch):
    compilation_output = {**PDF_OUTPUT, "output_path": "Lab02-肖奕然.pdf"}
    monkeypatch.setattr(
        "latexonhttp.api.builds.latexToPdf", lambda *args, **kwargs: compilation_output
    )

    response = build_client().post(
        "/builds/sync",
        data={
            "compiler": "xelatex",
            "file1": (
                io.BytesIO(
                    b"\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}"
                ),
                "Lab02-肖奕然.tex",
            ),
        },
    )

    assert response.status_code == 201
    assert response.data == PDF_OUTPUT["pdf"]
    disposition = response.headers["Content-Disposition"]
    # The whole header value must be ASCII-safe for every WSGI server.
    disposition.encode("ascii")
    assert disposition == (
        'inline; filename="Lab02-%E8%82%96%E5%A5%95%E7%84%B6.pdf"; '
        "filename*=UTF-8''Lab02-%E8%82%96%E5%A5%95%E7%84%B6.pdf"
    )
    _, options = parse_options_header(disposition)
    assert options["filename"] == "Lab02-肖奕然.pdf"


def test_sync_response_header_for_ascii_filename(monkeypatch):
    compilation_output = {**PDF_OUTPUT, "output_path": "output.pdf"}
    monkeypatch.setattr(
        "latexonhttp.api.builds.latexToPdf", lambda *args, **kwargs: compilation_output
    )

    response = build_client().post(
        "/builds/sync",
        json={"resources": [{"main": True, "content": "test"}]},
    )

    assert response.status_code == 201
    assert response.headers["Content-Disposition"] == 'inline; filename="output.pdf"'
