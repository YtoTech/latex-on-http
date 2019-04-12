# -*- coding: utf-8 -*-
"""
    latexonhttp.app
    ~~~~~~~~~~~~~~~~~~~~~
    Server application for Latex On HTTP API.
    Here are exposed the Rest API endpoints.

    :copyright: (c) 2017-2018 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
from flask import Flask, request, jsonify
from latexonhttp.api.builds import builds_app
from latexonhttp.api.fonts import fonts_app
from latexonhttp.api.projects import projects_app
from latexonhttp.api.packages import packages_app

app = Flask(__name__)
app.register_blueprint(builds_app, url_prefix="/builds")
app.register_blueprint(fonts_app, url_prefix="/fonts")
app.register_blueprint(projects_app, url_prefix="/projects")
app.register_blueprint(packages_app, url_prefix="/packages")


@app.route("/")
def hello():
    # TODO Distribute documentation. (HTML)
    # TODO Add endpoints links / HATEOAS.
    # TODO Return an OpenAPI specification
    # https://github.com/OAI/OpenAPI-Specification
    return (
        jsonify(
            {
                "message": "Welcome to the Latex on HTTP API",
                "source": "https://github.com/YtoTech/latex-on-http",
            }
        ),
        200,
    )
