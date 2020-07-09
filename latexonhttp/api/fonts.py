# -*- coding: utf-8 -*-
"""
    latexonhttp.api.fonts
    ~~~~~~~~~~~~~~~~~~~~~
    Manage LaTeX-On-HTTP fonts.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
from flask import Blueprint, jsonify
from fclist import fclist

fonts_app = Blueprint("fonts", __name__)


@fonts_app.route("", methods=["GET"])
def fonts_list():
    fonts = []
    for font in fclist():
        fonts.append(
            {"family": font.family, "name": font.fullname, "styles": list(font.style)}
        )
    # TODO Group by families?
    return (jsonify({"fonts": fonts}), 200)
