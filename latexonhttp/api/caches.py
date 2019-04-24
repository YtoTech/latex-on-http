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
from latexonhttp.caching.store import get_cache_metadata

from pprint import pformat

logger = logging.getLogger(__name__)

caches_app = Blueprint("caches", __name__)


@caches_app.route("/resources", methods=["GET"])
def resources_metadata():
    return (jsonify(get_cache_metadata()), 200)


# TODO Check for a list of resource hashes to know if there are cached.
# POST:/caches/resources/check_cached
