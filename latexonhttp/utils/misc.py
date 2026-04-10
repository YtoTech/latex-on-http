# -*- coding: utf-8 -*-
"""
latexonhttp.utils.misc
~~~~~~~~~~~~~~~~~~~~~
LaTeX-On-HTTP miscellaneous utils.

:copyright: (c) 2019-2022 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

CURRENT_API_VERSION = "2026-04-10-3"


def get_api_version():
    global CURRENT_API_VERSION
    return CURRENT_API_VERSION
