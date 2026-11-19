"""
latexonhttp.docs
~~~~~~~~~~~~~~~~
Serve the statically-built documentation site (API reference, guides,
playground), built from docs/site to docs/_build/ by the Node/Eleventy
build (see the Dockerfile docs-builder stage or `make build-docs`).

:copyright: (c) 2026 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

import os

from flask import Blueprint, abort, redirect, send_from_directory, url_for

docs_app = Blueprint("docs", __name__)

# Build output of the documentation site, relative to the repository root
# (the parent directory of this package).
DOCUMENTATION_BUILD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs",
    "_build",
)


@docs_app.route("/docs")
def documentation_redirect():
    """Redirect to the canonical /docs/ documentation URL."""
    return redirect(url_for(".documentation"))


@docs_app.route("/docs/", defaults={"docs_path": ""})
@docs_app.route("/docs/<path:docs_path>")
def documentation(docs_path):
    """Serve the static documentation site built at docs/_build/."""
    if not os.path.isdir(DOCUMENTATION_BUILD_DIR):
        return (
            {
                "error": "DOCUMENTATION_NOT_BUILT",
                "message": (
                    "The documentation site is not built. "
                    "Run 'make build-docs' (npm) in the repository."
                ),
            },
            404,
        )
    # Default document, and pretty-URL handling (/docs/guides/server/).
    relative_path = docs_path
    if not relative_path or relative_path.endswith("/"):
        relative_path = (relative_path or "") + "index.html"
    if not os.path.isfile(os.path.join(DOCUMENTATION_BUILD_DIR, relative_path)):
        pretty_url_candidate = relative_path.rstrip("/") + "/index.html"
        if os.path.isfile(os.path.join(DOCUMENTATION_BUILD_DIR, pretty_url_candidate)):
            relative_path = pretty_url_candidate
        else:
            abort(404)
    # send_from_directory guards against path traversal.
    return send_from_directory(DOCUMENTATION_BUILD_DIR, relative_path, max_age=600)
