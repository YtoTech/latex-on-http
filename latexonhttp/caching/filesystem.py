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


def get_cache_entry_path(hash):
    return os.path.abspath("{}/{}".format(get_cache_root_path(), hash))


def action_reset_cache(action):
    cache_directory_path = get_cache_root_path()
    if os.path.exists(cache_directory_path):
        shutil.rmtree(cache_directory_path)


def action_add_resource_to_cache(action):
    resource_hash = action["resource"]["data_spec"]["hash"]
    resource_cache_entry_path = get_cache_entry_path(resource_hash)
    logger.info(
        "Writing cache entry %s to %s ...", resource_hash, resource_cache_entry_path
    )
    os.makedirs(os.path.dirname(resource_cache_entry_path), exist_ok=True)
    with open(resource_cache_entry_path, "wb") as f:
        bytes_written = f.write(action["data"])
        logger.debug("Wrote %d bytes to cache %s", bytes_written, resource_hash)
    # TODO Sanity check.


def action_remove_resource_from_cache(action):
    resource_hash = action["resource"]["hash"]
    resource_cache_entry_path = get_cache_entry_path(resource_hash)
    logger.info(
        "Removing cache entry %s from %s ...", resource_hash, resource_cache_entry_path
    )
    os.remove(resource_cache_entry_path)
    logger.debug(
        "Removed %d bytes from cache %s", action["resource"]["size"], resource_hash
    )
    # TODO Sanity check?


CACHE_ACTIONS = {
    "reset_cache": action_reset_cache,
    "add_resource": action_add_resource_to_cache,
    "remove_resource": action_remove_resource_from_cache,
}


def apply_cache_action(action):
    action_fn = CACHE_ACTIONS.get(action["name"])
    if not action_fn:
        raise RuntimeError("No cache action for {}".format(action["name"]))
    logger.info("Applying cache action: %s ...", {**action, "data": None})
    action_fn(action)


# TODO Cache metadata <> filesystem reality sanity checks.
