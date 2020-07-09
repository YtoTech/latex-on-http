# -*- coding: utf-8 -*-
"""
    latexonhttp.caching.filesystem
    ~~~~~~~~~~~~~~~~~~~~~
    Filesystem driver / management for LaTeX-On-HTTP cache.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import logging
import shutil
import os.path
from latexonhttp.caching.store import get_cache_metadata
from latexonhttp.resources.utils import process_resource_data_spec


logger = logging.getLogger(__name__)

# TODO How will it behave with multi-threads?
CACHE_DIRECTORY = "./tmp/loh_cache"
# 200 Mo.
MAX_RESOURCES_CACHE_SIZE = 200 * 1000000
ENABLE_SANITY_CHECKS = True


# -------------------------------------
# External API.
# -------------------------------------


def apply_cache_action(action):
    logger.info("Applying cache action: %s ...", {**action, "data": None})
    action_fn = CACHE_ACTIONS.get(action["name"])
    if not action_fn:
        raise RuntimeError("No cache action for {}".format(action["name"]))
    action_fn(action)


def get_cached_data(resource_hash):
    resource_cache_entry_path = get_cache_entry_path(resource_hash)
    with open(resource_cache_entry_path, "rb") as f:
        cached_data = f.read()
    if ENABLE_SANITY_CHECKS:
        data_spec = process_resource_data_spec(cached_data)
        if data_spec["hash"] != resource_hash:
            raise RuntimeError(
                "Cache data read not matching hash {} != {}".format(
                    data_spec["hash"], resource_hash
                )
            )
    return cached_data


# -------------------------------------
# Actions.
# -------------------------------------


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


CACHE_ACTIONS = {
    "reset_cache": action_reset_cache,
    "add_resource": action_add_resource_to_cache,
    "remove_resource": action_remove_resource_from_cache,
}

# -------------------------------------
# Working bits.
# -------------------------------------


def get_cache_root_path():
    return os.path.abspath(CACHE_DIRECTORY)


def get_cache_entry_path(hash):
    return os.path.abspath("{}/{}".format(get_cache_root_path(), hash))


def get_on_disk_cache_actual_size():
    return sum(
        os.path.getsize(os.path.join(dirpath, filename))
        for dirpath, dirnames, filenames in os.walk(get_cache_root_path())
        for filename in filenames
    )


def total_size_check(cache_metadata):
    if not cache_metadata.get("total_size"):
        return
    on_disk_total_size = get_on_disk_cache_actual_size()
    logger.debug(
        "On disk cache size: %d bytes ft. metadata total size: %d bytes",
        on_disk_total_size,
        cache_metadata["total_size"],
    )
    total_size_delta = on_disk_total_size - cache_metadata["total_size"]
    if total_size_delta != 0:
        logger.warning(
            "Cache sanity check failed, size difference is: %d bytes", total_size_delta
        )
        raise RuntimeError(
            "Cache sanity check failed, size difference is: {} bytes".format(
                total_size_delta
            )
        )
    return on_disk_total_size


def max_size_check(cache_metadata):
    if cache_metadata["total_size"] > MAX_RESOURCES_CACHE_SIZE:
        raise RuntimeError(
            "Max cache size overthrow, current: {} bytes, max: {} bytes, delta: {} bytes".format(
                cache_metadata["total_size"],
                MAX_RESOURCES_CACHE_SIZE,
                cache_metadata["total_size"] - MAX_RESOURCES_CACHE_SIZE,
            )
        )


def apply_sanity_check():
    # Cache metadata <> filesystem reality sanity checks.
    cache_metadata = get_cache_metadata()
    total_size_check(cache_metadata)
    max_size_check(cache_metadata)
