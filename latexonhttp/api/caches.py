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
from latexonhttp.caching.resources import get_cache_metadata_snapshot

from pprint import pformat

logger = logging.getLogger(__name__)

caches_app = Blueprint("caches", __name__)

# TODO Make this route private to the admin:
# this allows to get all cache file hashes
# and to actually get the file content,
# by dumping them in Latex output.
# Only provide the checker endpoint to the public.
@caches_app.route("/resources", methods=["GET"])
def resources_metadata():
    return (jsonify(get_cache_metadata_snapshot()), 200)


# TODO Check for a list of resource hashes to know if there are cached.
# POST:/caches/resources/check_cached
