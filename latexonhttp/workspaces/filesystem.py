"""
latexonhttp.workspaces.filesystem
~~~~~~~~~~~~~~~~~~~~~
Filesystem driver / management for build workspaces.

:copyright: (c) 2019 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

import errno
import logging
import os.path
import shutil
import stat

logger = logging.getLogger(__name__)

CHECK_DATA_SPEC_SIZE_ESTIMATE = True
WORKSPACE_DIRECTORY = "./tmp/loh_workspaces"

# TODO Clean workspace directory on start/init?
# --> if there was an application error, the workspace is orphaned and not removed.


def is_safe_path(basedir, path, follow_symlinks=True):
    """Check path containment using path components, not string prefixes."""
    normalize = os.path.realpath if follow_symlinks else os.path.abspath
    normalized_base = normalize(basedir)
    normalized_path = normalize(path)
    try:
        return os.path.commonpath([normalized_base, normalized_path]) == normalized_base
    except ValueError:
        # Different drives on platforms that support them cannot be contained.
        return False


def get_workspace_root_path(workspace_id):
    return os.path.abspath(f"{WORKSPACE_DIRECTORY}/{workspace_id}")


def get_resource_fullpath(workspace_id, resource):
    return os.path.abspath(
        "{}/{}".format(get_workspace_root_path(workspace_id), resource["build_path"])
    )


def persist_resource_to_workspace(workspace_id, resource, data):
    workspace_path = get_workspace_root_path(workspace_id)
    resource_full_path = get_resource_fullpath(workspace_id, resource)
    if not is_safe_path(workspace_path, resource_full_path):
        return "INVALID_PATH"
    # TODO Id for identifying input resources.
    logger.info("Writing to %s ...", resource_full_path)
    os.makedirs(os.path.dirname(resource_full_path), exist_ok=True)
    if not is_safe_path(workspace_path, resource_full_path):
        return "INVALID_PATH"
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    file_descriptor = os.open(resource_full_path, flags, 0o600)
    with os.fdopen(file_descriptor, "wb") as f:
        bytes_written = f.write(data)
        logger.debug("Wrote %d bytes to %s", bytes_written, resource_full_path)
    if CHECK_DATA_SPEC_SIZE_ESTIMATE:
        check_data_spec_size_estimate(workspace_id, resource)


def read_generated_file(workspace_root, path, max_size):
    """Read a bounded regular workspace output and return data with an error."""

    def error_result(reason):
        return None, {
            "error": "GENERATED_FILE_READ_ERROR",
            "file_read_error": {
                "reason": reason,
                "path": os.path.relpath(path, workspace_root),
            },
        }

    if not is_safe_path(workspace_root, path):
        logger.warning("Cannot read compilation output outside workspace %s", path)
        return error_result("outside_workspace")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        file_descriptor = os.open(path, flags)
        with os.fdopen(file_descriptor, "rb") as fd:
            if not stat.S_ISREG(os.fstat(fd.fileno()).st_mode):
                logger.warning("Cannot read non-regular compilation output %s", path)
                return error_result("not_regular")
            data = fd.read(max_size + 1)
            if len(data) > max_size:
                logger.warning("Cannot read oversized compilation output %s", path)
                return error_result("too_large")
            return data, None
    except OSError as error:
        logger.warning("Cannot safely read compilation output %s: %s", path, error)
        if error.errno == errno.ENOENT:
            return error_result("not_found")
        if error.errno == errno.EISDIR:
            return error_result("not_regular")
        if error.errno == errno.ELOOP:
            return error_result("symlink")
        return error_result("read_error")


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
