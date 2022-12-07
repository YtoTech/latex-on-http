# -*- coding: utf-8 -*-
"""
    tests.test_inpuc_spec
    ~~~~~~~~~~~~~~~~~~~~~
    Tests on LaTeX-on-HTTP input spec.

    :copyright: (c) 2022 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import pytest
import json
import requests


def test_input_spec_must_include_a_list_resources(latex_on_http_api_url):
    """
    Compile a Latex document with a bibliography with biblatex.
    """
    r = requests.post(
        latex_on_http_api_url + "/builds/sync",
        json={"resources": '{"main": true, "content": ""}'},
    )
    assert r.status_code == 400
    assert r.json() == {
        "error": "INVALID_PAYLOAD_SHAPE",
        "shape_errors": {"resources": ["must be of list type"]},
        "input_spec_mode": "json",
        "input_spec": {"resources": '{"main": true, "content": ""}'},
    }
