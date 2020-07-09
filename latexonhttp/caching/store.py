# -*- coding: utf-8 -*-
"""
    latexonhttp.caching.store
    ~~~~~~~~~~~~~~~~~~~~~
    Caching metadata store for LaTeX-On-HTTP.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import logging

logger = logging.getLogger(__name__)

# TODO Store to Redis?
# So we can keep cache statistics between restarts.
# However requires to refresh the cache metadata from
# what is on the filesystem on startup
# (data on disk could have been erased or been corrupted).
CACHE_METADATA = None

# TODO These operations should/must fail (be forbidden)
# outside the cache process.


def get_cache_metadata():
    global CACHE_METADATA
    # Returns a copy?
    return CACHE_METADATA


def persist_cache_metadata(metadata):
    # TODO Only allows the API to send updates? (React-like)
    # logger.debug("Cache metadata update: %s", metadata)
    global CACHE_METADATA
    CACHE_METADATA = metadata
    return CACHE_METADATA
