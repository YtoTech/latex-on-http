# -*- coding: utf-8 -*-
"""
latexonhttp.resources.misc
~~~~~~~~~~~~~~~~~~~~~
Resources utils.

:copyright: (c) 2019 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

import hashlib
from urllib.parse import urlsplit, urlunsplit


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


def _redact_resource_url(url):
    """Keep routing metadata without persisting credentials or query secrets."""
    if not isinstance(url, str):
        return "<redacted>"
    try:
        parsed = urlsplit(url)
        # urlsplit port validation can be lazy, so force it before storing.
        parsed.port
        netloc = parsed.netloc.rpartition("@")[2]
        return urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))
    except ValueError:
        return "<invalid-url>"


def sanitize_input_spec_for_job(input_spec):
    """Return the input metadata safe to persist in a compilation job."""
    cleaned_spec = prune_resources_content_for_logging(input_spec)
    if not isinstance(cleaned_spec, dict):
        return cleaned_spec
    for resource in cleaned_spec.get("resources", []):
        if not isinstance(resource, dict):
            continue
        for source_key in ("url", "git", "tar"):
            if source_key in resource:
                resource[source_key] = _redact_resource_url(resource[source_key])
    return cleaned_spec
