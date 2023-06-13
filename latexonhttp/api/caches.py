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
from flask import Blueprint, request
from latexonhttp.caching.resources import (
    get_cache_metadata_snapshot,
    are_resources_in_cache,
    reset_cache,
)

from pprint import pformat

logger = logging.getLogger(__name__)

caches_app = Blueprint("caches", __name__)

# TODO Name the cache?
#    /caches/<cache name>/resources
# For eg.
#    /caches/input/resources
#    /caches/output/resources


@caches_app.route("/resources", methods=["GET"])
def resources_metadata():
    is_ok, cache_response = get_cache_metadata_snapshot()
    if not is_ok:
        return (cache_response, 500)
    return (map_cache_metadata_for_public(cache_response), 200)


@caches_app.route("/resources", methods=["DELETE"])
def resources_reset_cache():
    is_ok, cache_response = reset_cache()
    if not is_ok:
        return (cache_response, 500)
    return "", 204


@caches_app.route("/resources/check_cached", methods=["POST"])
def resources_check_cached():
    payload = request.get_json()
    if not payload:
        return {"error": "MISSING_PAYLOAD"}, 400
    if not "resources" in payload:
        return {"error": "MISSING_RESOURCES"}, 400
    for resource in payload["resources"]:
        if not "hash" in resource:
            return {"error": "MISSING_RESOURCE_HASH"}, 400
    is_ok, cache_response = are_resources_in_cache(payload["resources"])
    if not is_ok:
        return (cache_response, 500)
    return (
        {
            "resources": {
                resource["hash"]: {"hit": resource["hit"]}
                for resource in cache_response
            }
        },
        200,
    )


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
