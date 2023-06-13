# -*- coding: utf-8 -*-
"""
    latexonhttp.app
    ~~~~~~~~~~~~~~~~~~~~~
    Server application for LaTeX-On-HTTP API.
    Here are exposed the Rest API endpoints.

    :copyright: (c) 2017-2018 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import os
import logging.config
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from flask import Flask, request
from flask_cors import CORS
from latexonhttp.api.builds import builds_app
from latexonhttp.api.fonts import fonts_app
from latexonhttp.api.packages import packages_app
from latexonhttp.api.texlive import texlive_app
from latexonhttp.api.caches import caches_app
from latexonhttp.api.projects import projects_app
from latexonhttp.utils.misc import get_api_version
from latexonhttp.utils.texlive import get_texlive_version_spec

# Logging.
logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"default": {"format": "[%(levelname)s %(module)s] %(message)s"}},
        "handlers": {
            "console": {"class": "logging.StreamHandler", "formatter": "default"}
        },
        "loggers": {"latexonhttp": {"handlers": ["console"], "level": "DEBUG"}},
    }
)

if os.environ.get("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.environ["SENTRY_DSN"],
        integrations=[FlaskIntegration()],
        # By default the SDK will try to use the SENTRY_RELEASE
        # environment variable, or infer a git commit
        # SHA as release, however you may want to set
        # something more human-readable.
        release=get_api_version(),
    )

app = Flask(__name__)
app.register_blueprint(builds_app, url_prefix="/builds")
app.register_blueprint(fonts_app, url_prefix="/fonts")
app.register_blueprint(packages_app, url_prefix="/packages")
app.register_blueprint(texlive_app, url_prefix="/texlive")
app.register_blueprint(caches_app, url_prefix="/caches")
# TODO
# /users
# /projects
# In Fire-Latex layer as an extension?
# Keep this project centered on the Latex compiling features/abstractions,
# put the project/workspace/user management in another layer.
# app.register_blueprint(projects_app, url_prefix="/projects")

# Allows CORS requests on all endpoints.
CORS(app, resources={r"/*": {"origins": "*"}})


@app.route("/")
def hello():
    # TODO Distribute documentation. (HTML)
    # TODO Add endpoints links / HATEOAS.
    # TODO Return an OpenAPI specification
    # https://github.com/OAI/OpenAPI-Specification
    return (
        {
            "message": "Welcome to the LaTeX-On-HTTP API",
            "version": get_api_version(),
            "source": "https://github.com/YtoTech/latex-on-http",
            "documentation": "https://github.com/YtoTech/latex-on-http",
            "texlive_version": get_texlive_version_spec()["texlive"]["version"],
        },
        200,
    )
