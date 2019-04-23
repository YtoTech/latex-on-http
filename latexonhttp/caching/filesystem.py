# -*- coding: utf-8 -*-
"""
    latexonhttp.caching.filesystem
    ~~~~~~~~~~~~~~~~~~~~~
    Filesystem driver / management for Latex-On-HTTP cache.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import logging
import shutil
import os.path


logger = logging.getLogger(__name__)

# TODO How will it behave with multi-threads?
CACHE_DIRECTORY = "./tmp/loh_cache"


def get_cache_root_path():
    return os.path.abspath(CACHE_DIRECTORY)


def action_reset_cache(action):
    cache_directory_path = get_cache_root_path()
    if os.path.exists(cache_directory_path):
        shutil.rmtree(cache_directory_path)


CACHE_ACTIONS = {"reset_cache": action_reset_cache}


def apply_cache_actions(actions):
    for action in actions:
        action_fn = CACHE_ACTIONS.get(action["name"])
        if not action_fn:
            raise RuntimeError("No cache action for {}".format(action["name"]))
        logger.info("Applying cache action: %s ...", action)
        action_fn(action)


# TODO Cache metadata <> filesystem reality sanity checks.
