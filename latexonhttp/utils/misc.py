# -*- coding: utf-8 -*-
"""
    latexonhttp.utils.misc
    ~~~~~~~~~~~~~~~~~~~~~
    Latex-On-HTTP miscellaneous utils.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import subprocess

CURRENT_API_VERSION = None


def get_api_version():
    global CURRENT_API_VERSION
    if not CURRENT_API_VERSION:
        CURRENT_API_VERSION = (
            subprocess.check_output(["git", "describe", "--always"])
            .strip()
            .decode("utf-8")
        )
    return CURRENT_API_VERSION
