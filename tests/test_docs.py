"""
tests.test_docs
~~~~~~~~~~~~~~~
The documentation site is served from the /docs/ route.

Unit-tier: uses the Flask test client, no LaTeX and no running app required.
Skipped gracefully when the documentation site has not been built yet
(run `make build-docs`).
"""

import os

import pytest

from latexonhttp.app import app
from latexonhttp.docs import DOCUMENTATION_BUILD_DIR


@pytest.fixture(scope="module")
def docs_client():
    app.config["TESTING"] = True
    return app.test_client()


def docs_built():
    return os.path.exists(os.path.join(DOCUMENTATION_BUILD_DIR, "index.html"))


pytestmark = pytest.mark.skipif(
    not docs_built(),
    reason=(
        "The documentation site is not built (docs/_build/ missing);"
        " run 'make build-docs'."
    ),
)


def test_docs_index(docs_client):
    """The documentation index page is served."""
    response = docs_client.get("/docs/")
    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert b"LaTeX" in response.data
    # The playground is linked from the landing page.
    assert b"playground/index.html" in response.data


def test_docs_canonical_redirect(docs_client):
    """/docs redirects to /docs/."""
    response = docs_client.get("/docs")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/docs/")


def test_docs_assets(docs_client):
    """Static assets of the site are served."""
    response = docs_client.get("/docs/assets/css/styles.css")
    assert response.status_code == 200
    assert response.mimetype == "text/css"


def test_docs_playground_page_and_config(docs_client):
    """The playground page embeds its endpoint configuration."""
    response = docs_client.get("/docs/playground/")
    assert response.status_code == 200
    assert b'id="pg-config"' in response.data


def test_docs_pretty_url_fallback(docs_client):
    """Pretty URLs resolve the underlying index.html."""
    response = docs_client.get("/docs/guides/server")
    assert response.status_code == 200
    assert response.mimetype == "text/html"


def test_docs_unknown_page_404(docs_client):
    """Unknown documentation paths are a 404."""
    response = docs_client.get("/docs/not-a-page/")
    assert response.status_code == 404


def test_docs_path_traversal_blocked(docs_client):
    """Directory traversal is not allowed."""
    response = docs_client.get("/docs/..%2f..%2fpyproject.toml")
    assert response.status_code == 404
