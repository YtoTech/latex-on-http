# -*- coding: utf-8 -*-
"""
    latexonhttp.workspaces.filesystem
    ~~~~~~~~~~~~~~~~~~~~~
    Filesystem driver / management for build workspaces.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import logging
import os.path
import shutil

logger = logging.getLogger(__name__)

CHECK_DATA_SPEC_SIZE_ESTIMATE = True
WORKSPACE_DIRECTORY = "./tmp/loh_workspaces"

# TODO Clean workspace directory on start/init?
# --> if there was an application error, the workspace is orphaned and not removed.


def is_safe_path(basedir, path, follow_symlinks=False):
    # https://security.openstack.org/guidelines/dg_using-file-paths.html
    # resolves symbolic links
    if follow_symlinks:
        return os.path.realpath(path).startswith(basedir)
    return os.path.abspath(path).startswith(basedir)


def get_workspace_root_path(workspace_id):
    return os.path.abspath("{}/{}".format(WORKSPACE_DIRECTORY, workspace_id))


def get_resource_fullpath(workspace_id, resource):
    return os.path.abspath(
        "{}/{}".format(get_workspace_root_path(workspace_id), resource["build_path"])
    )


def persist_resource_to_workspace(workspace_id, resource, data):
    resource_full_path = get_resource_fullpath(workspace_id, resource)
    if not is_safe_path(get_workspace_root_path(workspace_id), resource_full_path):
        return "INVALID_PATH"
    # TODO Id for identifying input resources.
    logger.info("Writing to %s ...", resource_full_path)
    os.makedirs(os.path.dirname(resource_full_path), exist_ok=True)
    with open(resource_full_path, "wb") as f:
        bytes_written = f.write(data)
        logger.debug("Wrote %d bytes to %s", bytes_written, resource_full_path)
    if CHECK_DATA_SPEC_SIZE_ESTIMATE:
        check_data_spec_size_estimate(workspace_id, resource)


def make_workspace(workspace_id):
    workspace_path = get_workspace_root_path(workspace_id)
    logger.info("Creating workspace directory %s", workspace_path)
    os.makedirs(workspace_path)


def delete_workspace(workspace_id):
    workspace_path = get_workspace_root_path(workspace_id)
    logger.info("Deleting workspace directory %s", workspace_path)
    shutil.rmtree(workspace_path)


def check_data_spec_size_estimate(workspace_id, resource):
    size_on_disk = os.path.getsize(get_resource_fullpath(workspace_id, resource))
    logger.debug(
        "Size on disk: %d ft. Size est: %s", size_on_disk, resource["data_spec"]["size"]
    )
    if size_on_disk != resource["data_spec"]["size"]:
        logger.warning(
            "Resource %s size estimate (%s) mismatch with size on disk (%d)",
            resource["data_spec"]["size"],
            size_on_disk,
            resource["build_path"],
        )
