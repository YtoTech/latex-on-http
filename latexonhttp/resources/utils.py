# -*- coding: utf-8 -*-
"""
latexonhttp.resources.misc
~~~~~~~~~~~~~~~~~~~~~
Resources utils.

:copyright: (c) 2019 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

import hashlib
import sys


def process_resource_data_spec(data):
    return {
        "hash": "sha256:{}".format(hashlib.sha256(data).hexdigest()),
        # What we would like it too have an accurate estimation of size
        # (when written) on disk of the data (not on memory).
        "size": len(data),
    }


def prune_resources_content_for_logging(input_spec):
    """Redact resource content without interpreting malformed request shapes."""
    if not isinstance(input_spec, dict):
        return input_spec
    resources = input_spec.get("resources", [])
    if not isinstance(resources, list):
        return input_spec
    return {
        **input_spec,
        "resources": [
            (
                {
                    **resource,
                    "content": "content" in resource,
                    "file": "file" in resource,
                }
                if isinstance(resource, dict)
                else resource
            )
            for resource in resources
        ],
    }
