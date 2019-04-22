# -*- coding: utf-8 -*-
"""
    latexonhttp.api.builds
    ~~~~~~~~~~~~~~~~~~~~~
    Manage Latex builds / compilations.

    :copyright: (c) 2017-2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import logging
import uuid
import urllib.request
import os.path
import base64
from flask import Blueprint, request, jsonify, Response
from latexonhttp.compiler import latexToPdf
from latexonhttp.resources.normalization import normalize_resources_input
from latexonhttp.resources.validation import check_resources_prefetch
from latexonhttp.resources.fetching import fetch_resources

from pprint import pformat

logger = logging.getLogger(__name__)

builds_app = Blueprint("builds", __name__)


def is_safe_path(basedir, path, follow_symlinks=False):
    # resolves symbolic links
    if follow_symlinks:
        return os.path.realpath(path).startswith(basedir)
    return os.path.abspath(path).startswith(basedir)


# TODO Extract the filesystem management in a module:
# - determine of fs/files actions to get to construct the filesystem;
# - support content/string, base64/file, url/file, url/git, url/tar, post-data/tar
# - hash and make a (deterministic) signature of files uploaded;
# - from the list of actions, prepare the file system (giving only a root directory);
# (- add a cache management on the file system preparation subpart).
#
# The compiler only uses:
# - the hash for an eventual output cache
# (if entire input signature match a cached output file, just return this file);
# - the prepared directory of files where the build happens.

# Persist cached files.
# Endpoint for checking if inputs (or output) are cached,
# for smart client use.

# TODO Only register request here, and allows to define an hook for when
# the work is done?
# Allows the two: (async, sync)
@builds_app.route("/sync", methods=["POST"])
def compiler_latex():
    # TODO Distribute documentation. (HTML)
    payload = request.get_json()
    if not payload:
        return jsonify("MISSING_PAYLOAD"), 400

    # TODO Pre-normalized data checks.
    # - resources (mandatory, must be an array).
    # TODO High-level normalizsation.
    # - compiler
    # Choose compiler: latex, pdflatex, xelatex or lualatex
    # We default to pdflatex.
    compilerName = "pdflatex"
    if "compiler" in payload:
        if payload["compiler"] not in ["latex", "lualatex", "xelatex", "pdflatex"]:
            return jsonify("INVALID_COMPILER"), 400
        compilerName = payload["compiler"]
    if not "resources" in payload:
        return jsonify("MISSING_RESOURCES"), 400

    # -------------
    # Pre-fetch normalization and checks.
    # -------------
    normalized_resources = normalize_resources_input(payload["resources"])
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(pformat(normalized_resources))
    # - Prefetch checks (paths, main document, ...);
    errors = check_resources_prefetch(normalized_resources)
    if errors:
        return jsonify(errors[0]), 400

    # -------------
    # Fetching, post-fetch normalization and checks, filesystem creation.
    # -------------

    workspace_id = str(uuid.uuid4())
    workspace_path = os.path.abspath("./tmp/" + workspace_id)

    def on_fetched(resource, data):
        logger.debug("Fetched %s: %s bytes", resource["build_path"], len(data))
        # TODO Persist to filesystem;
        # TODO Hash and normalize fetched inputs;
        # TODO Input cache forwarding.
        # --> in a module (filesystem.persist or storage.persist, or workspace.persist)
        # https://security.openstack.org/guidelines/dg_using-file-paths.html
        resource["workspace"] = {
            "build_path": os.path.abspath(workspace_path + "/" + resource["build_path"])
        }
        if not is_safe_path(workspace_path, resource["workspace"]["build_path"]):
            return jsonify("INVALID_PATH"), 400
        # TODO Id for input resources.
        logger.info("Writing to %s ...", resource["workspace"]["build_path"])
        os.makedirs(os.path.dirname(resource["workspace"]["build_path"]), exist_ok=True)
        with open(resource["workspace"]["build_path"], "wb") as f:
            bytes_written = f.write(data)
            logger.debug(
                "Wrote %d bytes to %s ...",
                bytes_written,
                resource["workspace"]["build_path"],
            )

    # TODO Input cache provider.
    error = fetch_resources(normalized_resources, on_fetched)
    if error:
        return jsonify(error), 400
    # TODO
    # - Process build global signature/hash (compiler, resource hashes, other options...)

    # mainResource = None
    # workspaceId = str(uuid.uuid4())
    # workspacePath = os.path.abspath("./tmp/" + workspaceId)
    # for resource in payload["resources"]:
    #     # Must have:
    #     # Either data or url.
    #     if "main" in resource and resource["main"] is True:
    #         mainResource = resource
    #     # TODO Be immutable and preserve the original content payload.
    #     if "url" in resource:
    #         # Fetch and put in resource content.
    #         # TODO Handle errors (404, network, etc.).
    #         print("Fetching {} ...".format(resource["url"]))
    #         resource["content"] = urllib.request.urlopen(resource["url"]).read()
    #         # Decode if main file?
    #         if "main" in resource and resource["main"] is True:
    #             resource["content"] = resource["content"].decode("utf-8")
    #     if "file" in resource:
    #         resource["content"] = base64.b64decode(resource["file"])
    #     if not "content" in resource:
    #         return jsonify("MISSING_CONTENT"), 400
    #     # Path relative to the project.
    #     if "path" in resource:
    #         # Write file to workspace, if not the main file.
    #         if not "main" in resource or resource["main"] is not True:
    #             # https://security.openstack.org/guidelines/dg_using-file-paths.html
    #             resource["path"] = os.path.abspath(
    #                 workspacePath + "/" + resource["path"]
    #             )
    #             if not is_safe_path(workspacePath, resource["path"]):
    #                 return jsonify("INVALID_PATH"), 400
    #             print("Writing to {} ...".format(resource["path"]))
    #             os.makedirs(os.path.dirname(resource["path"]), exist_ok=True)
    #             if not "url" in resource and not "file" in resource:
    #                 resource["content"] = resource["content"].encode("utf-8")
    #             with open(resource["path"], "wb") as f:
    #                 f.write(resource["content"])
    # # TODO If more than one resource, must give a main file flag.
    # if len(payload["resources"]) == 1:
    #     mainResource = payload["resources"][0]
    # else:
    #     if not mainResource:
    #         return jsonify("MUST_SPECIFY_MAIN_RESOURCE"), 400

    # -------------
    # Compilation.
    # -------------

    # TODO Do an util to get main resource.
    main_resource = next(
        resource for resource in normalized_resources if resource["is_main_document"]
    )
    # TODO Try catch.
    latexToPdfOutput = latexToPdf(
        compilerName,
        # TODO Absolute directory.
        workspace_path,
        main_resource,
    )
    if not latexToPdfOutput["pdf"]:
        return (
            jsonify({"code": "COMPILATION_ERROR", "logs": latexToPdfOutput["logs"]}),
            400,
        )
    # TODO Specify ouput file name.
    # TODO Also return compilation logs here.
    # (So return a json. Include the PDF as base64 data?)
    # (In the long term it will be better to give a static URL to download
    # the generated PDF. We begin to talk about caching. This requires
    # lifecycle management. With something like a Redis.)
    # URL to get build result: PDF output, log, etc.
    # TODO In async / build status endpoint, returns:
    # - Normalized inputs;
    # - URLs for PDF output, log;
    return Response(
        latexToPdfOutput["pdf"],
        status="201",
        headers={"Content-Type": "application/pdf"},
    )
