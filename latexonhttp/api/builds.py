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

from pprint import pformat

logger = logging.getLogger(__name__)

builds_app = Blueprint("builds", __name__)


def is_safe_path(basedir, path, follow_symlinks=False):
    # resolves symbolic links
    if follow_symlinks:
        return os.path.realpath(path).startswith(basedir)
    return os.path.abspath(path).startswith(basedir)


# TODO Only register request here, and allows to define an hook for when
# the work is done?
# Allows the two: (async, sync)
@builds_app.route("/sync", methods=["POST"])
def compiler_latex():
    # TODO Distribute documentation. (HTML)
    payload = request.get_json()
    if not payload:
        return jsonify("MISSING_PAYLOAD"), 400
    # Choose compiler: latex, pdflatex, xelatex or lualatex
    # We default to pdflatex.
    compilerName = "pdflatex"
    # TODO Choose them directly from the method?
    if "compiler" in payload:
        if payload["compiler"] not in ["latex", "lualatex", "xelatex", "pdflatex"]:
            return jsonify("INVALID_COMPILER"), 400
        compilerName = payload["compiler"]
    if not "resources" in payload:
        return jsonify("MISSING_RESOURCES"), 400
    # TODO Must be an array.
    # Iterate on resources.

    normalized_resources = normalize_resources_input(payload["resources"])
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(pformat(normalized_resources))
    errors = check_resources_prefetch(normalized_resources)
    if errors:
        return jsonify(errors[0]), 400
    # TODO
    # - Prefetch checks (paths, main document, ...);
    # - Fetch input body/data; (checks for fetching; caching)
    # (All in memory, then process? Or pass a filesystem writter function and flush on the fly to build storage?)
    # -> Memory: good if we cached output; hard for git; problematic if huge input volume;
    # -> DIsk on-the-fly: uncesserary (slow/operations) if cached output; but else simpler.
    # -˙Hash and normalize fetched inputs;
    # - Process build global signature/hash (compiler, resource hashes, other options...)

    mainResource = None
    workspaceId = str(uuid.uuid4())
    workspacePath = os.path.abspath("./tmp/" + workspaceId)
    for resource in payload["resources"]:
        # Must have:
        # Either data or url.
        if "main" in resource and resource["main"] is True:
            mainResource = resource
        # TODO Be immutable and preserve the original content payload.
        if "url" in resource:
            # Fetch and put in resource content.
            # TODO Handle errors (404, network, etc.).
            print("Fetching {} ...".format(resource["url"]))
            resource["content"] = urllib.request.urlopen(resource["url"]).read()
            # Decode if main file?
            if "main" in resource and resource["main"] is True:
                resource["content"] = resource["content"].decode("utf-8")
        if "file" in resource:
            resource["content"] = base64.b64decode(resource["file"])
        if not "content" in resource:
            return jsonify("MISSING_CONTENT"), 400
        # Path relative to the project.
        if "path" in resource:
            # Write file to workspace, if not the main file.
            if not "main" in resource or resource["main"] is not True:
                # https://security.openstack.org/guidelines/dg_using-file-paths.html
                resource["path"] = os.path.abspath(
                    workspacePath + "/" + resource["path"]
                )
                if not is_safe_path(workspacePath, resource["path"]):
                    return jsonify("INVALID_PATH"), 400
                print("Writing to {} ...".format(resource["path"]))
                os.makedirs(os.path.dirname(resource["path"]), exist_ok=True)
                if not "url" in resource and not "file" in resource:
                    resource["content"] = resource["content"].encode("utf-8")
                with open(resource["path"], "wb") as f:
                    f.write(resource["content"])
    # TODO If more than one resource, must give a main file flag.
    if len(payload["resources"]) == 1:
        mainResource = payload["resources"][0]
    else:
        if not mainResource:
            return jsonify("MUST_SPECIFY_MAIN_RESOURCE"), 400
    # TODO Try catch.
    latexToPdfOutput = latexToPdf(
        compilerName,
        # TODO Absolute directory.
        workspacePath,
        mainResource["content"],
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
    # TODO In async / build status endpoint, returns:
    # - Normalized inputs;
    # -
    return Response(
        latexToPdfOutput["pdf"],
        status="201",
        headers={"Content-Type": "application/pdf"},
    )
