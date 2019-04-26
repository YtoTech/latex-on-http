# -*- coding: utf-8 -*-
"""
    latexonhttp.api.caches
    ~~~~~~~~~~~~~~~~~~~~~
    Caches endpoints, used to get a view on caches usage
    and to allow smart-client optimization (server-cache use).

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import logging
from flask import Blueprint, request, jsonify, Response
from latexonhttp.caching.resources import (
    get_cache_metadata_snapshot,
    are_resources_in_cache,
)

from pprint import pformat

logger = logging.getLogger(__name__)

caches_app = Blueprint("caches", __name__)


@caches_app.route("/resources", methods=["GET"])
def resources_metadata():
    return (jsonify(map_cache_metadata_for_public(get_cache_metadata_snapshot())), 200)


@caches_app.route("/resources/check_cached", methods=["POST"])
def resources_check_cached():
    payload = request.get_json()
    if not payload:
        return jsonify("MISSING_PAYLOAD"), 400
    if not "resources" in payload:
        return jsonify("MISSING_RESOURCES"), 400
    for resource in payload["resources"]:
        if not "hash" in resource:
            return jsonify("MISSING_RESOURCE_HASH"), 400
    return (jsonify({"resources": are_resources_in_cache(payload["resources"])}), 200)


def map_cache_metadata_for_public(cache_metadata):
    # Filter out cache entries (or at least their hashes),
    # because they would potentially allow user to get
    # any cache file content (by dumping them in Latex output).
    return {
        **cache_metadata,
        "cached_resources": [
            {"size": cached_resource["size"]}
            for cached_resource in cache_metadata["cached_resources"].values()
        ],
    }
