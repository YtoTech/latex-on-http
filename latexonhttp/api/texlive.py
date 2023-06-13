# -*- coding: utf-8 -*-
"""
    latexonhttp.api.texlive
    ~~~~~~~~~~~~~~~~~~~~~
    Information about LaTeX-On-HTTP TeXLive installation.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
from flask import Blueprint
from latexonhttp.utils.texlive import get_texlive_version_spec

texlive_app = Blueprint("texlive", __name__)


@texlive_app.route("information", methods=["GET"])
def texlive_installation_information():
    return (get_texlive_version_spec(), 200)
