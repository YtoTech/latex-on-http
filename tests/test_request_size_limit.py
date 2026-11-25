"""
tests.test_request_size_limit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Oversized request bodies are rejected with 413 REQUEST_TOO_LARGE.

:copyright: (c) 2026 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

import io

import pytest
import requests
from flask import Flask

from latexonhttp.api.builds import builds_app
from latexonhttp.docs import docs_app

# The unit-tier test app pins the limit low so oversized bodies fit in a
# few KB (the production default is 40 MiB, see MAX_REQUEST_BODY_BYTES).
LIMIT = 1024


@pytest.fixture(autouse=True)
def disable_job_tracking(monkeypatch):
    monkeypatch.setattr("latexonhttp.api.builds.create_job", lambda _metadata: None)
    monkeypatch.setattr(
        "latexonhttp.api.builds.update_job", lambda *_args, **_kwargs: None
    )


def build_client():
    test_app = Flask(__name__)
    test_app.config["MAX_CONTENT_LENGTH"] = LIMIT
    test_app.register_blueprint(builds_app, url_prefix="/builds")
    # Registered (like in the real app) so error responses can build their
    # /docs/ documentation links via url_for.
    test_app.register_blueprint(docs_app)
    return test_app.test_client()


def test_oversized_json_body_returns_413_request_too_large():
    response = build_client().post(
        "/builds/sync",
        json={"resources": [{"main": True, "content": "x" * (LIMIT + 1024)}]},
    )

    assert response.status_code == 413
    payload = response.get_json()
    assert payload["error"] == "REQUEST_TOO_LARGE"
    assert str(LIMIT) in payload["message"]
    assert payload["documentation"].endswith("/docs/api/builds-sync/")


def test_oversized_multipart_body_returns_413_request_too_large():
    data = {
        "file1": (io.BytesIO(b"x" * (LIMIT + 1024)), "big.tex"),
        "resources": '[{"main": "true", "multipart": "file1"}]',
    }
    response = build_client().post(
        "/builds/sync",
        data=data,
        content_type="multipart/form-data",
    )

    assert response.status_code == 413
    payload = response.get_json()
    assert payload["error"] == "REQUEST_TOO_LARGE"


def test_body_under_limit_still_reaches_validation():
    response = build_client().post("/builds/sync", json={"resources": []})

    assert response.status_code == 400
    assert response.get_json()["error"] == "MISSING_COMPILATION_SPECIFICATION"


def test_integration_oversized_body_is_rejected(latex_on_http_api_url):
    """End to end (gunicorn): a body over MAX_REQUEST_BODY_BYTES (pinned to
    1 MiB in docker-compose.test.yml) gets the JSON 413 contract."""
    spec = {
        "resources": [
            {
                "main": True,
                "content": "\\documentclass{article}\n\\begin{document}\n"
                + "x" * 1_100_000
                + "\n\\end{document}",
            }
        ]
    }
    r = requests.post(latex_on_http_api_url + "/builds/sync", json=spec)

    assert r.status_code == 413
    payload = r.json()
    assert payload["error"] == "REQUEST_TOO_LARGE"
    assert str(1048576) in payload["message"]
    assert payload["documentation"].endswith("/docs/api/builds-sync/")


def test_integration_body_under_limit_is_still_compiled(latex_on_http_api_url):
    """A body just under the 1 MiB test limit compiles normally, so the cap
    does not break ordinary (if large) documents."""
    spec = {
        "resources": [
            {
                "main": True,
                # Comment padding: grows the body without affecting the PDF.
                "content": "\\documentclass{article}\n\\begin{document}\n"
                + "%x" * 400_000
                + "Hello World\n\\end{document}",
            }
        ]
    }
    r = requests.post(latex_on_http_api_url + "/builds/sync", json=spec)

    assert r.status_code == 201
