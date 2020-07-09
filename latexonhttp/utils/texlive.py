# -*- coding: utf-8 -*-
"""
    latexonhttp.utils.texlive
    ~~~~~~~~~~~~~~~~~~~~~
    LaTeX-On-HTTP TeX Live utils.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import subprocess
from texlivemetadata import get_texlive_version_information

TEXLIVE_VERSION_SPEC = None


def get_texlive_version_spec():
    global TEXLIVE_VERSION_SPEC
    if not TEXLIVE_VERSION_SPEC:
        TEXLIVE_VERSION_SPEC = get_texlive_version_information()
    return TEXLIVE_VERSION_SPEC
