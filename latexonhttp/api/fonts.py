"""
latexonhttp.api.fonts
~~~~~~~~~~~~~~~~~~~~~
Manage LaTeX-On-HTTP fonts.

:copyright: (c) 2019 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

from fclist import fclist
from flask import Blueprint

fonts_app = Blueprint("fonts", __name__)


@fonts_app.route("", methods=["GET"])
def fonts_list():
    fonts = []
    for font in fclist():
        fonts.append(
            {"family": font.family, "name": font.fullname, "styles": list(font.style)}
        )
    # TODO Group by families?
    return ({"fonts": fonts}, 200)
