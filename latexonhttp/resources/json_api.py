# -*- coding: utf-8 -*-
"""
    latexonhttp.resources.json_api
    ~~~~~~~~~~~~~~~~~~~~~
    HTTP json API for compilation resources specification.

    :copyright: (c) 2020 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import logging
import pprint
import glom

logger = logging.getLogger(__name__)

PAYLOAD_KEYS_TO_COPY = ["compiler", "resources", "options"]


def parse_json_resources_spec(json_payload):
    if not json_payload:
        return None, None
    json_spec = {}

    # Select / copy several keys.
    for entry_key in (
        entry_key for entry_key in json_payload if entry_key in PAYLOAD_KEYS_TO_COPY
    ):
        json_spec[entry_key] = json_payload[entry_key]

    # Auto-spread options. entries.
    for option_key in (
        param_key for param_key in json_payload if "options." in param_key
    ):
        glom.assign(json_spec, option_key, json_payload[option_key], missing=dict)

    return json_spec, None
