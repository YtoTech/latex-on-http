# -*- coding: utf-8 -*-
"""
    latexonhttp.api.builds
    ~~~~~~~~~~~~~~~~~~~~~
    Manage Latex builds / compilations.

    :copyright: (c) 2017-2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import envparse
import logging
import pprint
import json
import glom
import cerberus
from flask import Blueprint, request
from latexonhttp.compiler import (
    latexToPdf,
    AVAILABLE_LATEX_COMPILERS,
    AVAILABLE_BIBLIOGRAPHY_COMMANDS,
)
from latexonhttp.resources.normalization import normalize_resources_input
from latexonhttp.resources.validation import check_resources_prefetch
from latexonhttp.resources.fetching import fetch_resources
from latexonhttp.resources.utils import (
    process_resource_data_spec,
    prune_resources_content_for_logging,
)
from latexonhttp.resources.multipart_api import parse_multipart_resources_spec
from latexonhttp.resources.querystring_api import parse_querystring_resources_spec
from latexonhttp.resources.json_api import parse_json_resources_spec
from latexonhttp.workspaces.lifecycle import create_workspace, remove_workspace
from latexonhttp.workspaces.filesystem import (
    get_workspace_root_path,
    persist_resource_to_workspace,
)
from latexonhttp.caching.resources import (
    forward_resource_to_cache,
    get_resource_from_cache,
)


logger = logging.getLogger(__name__)

builds_app = Blueprint("builds", __name__)
KEEP_WORKSPACE_DIR = envparse.env("KEEP_WORKSPACE_DIR", cast=bool, default=False)
KEEP_WORKSPACE_DIR_ON_ERROR = envparse.env(
    "KEEP_WORKSPACE_DIR_ON_ERROR", cast=bool, default=False
)


# TODO Extract the filesystem/workspace management in a module:
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
# TODO Returns the build job id in a response HTTP header.
# TODO Make a commond implementation for both async and sync, using a message broker.
# TODO Store jobs in a Redis, to be flushed.
# TODO With this job store, add top-level cache:
# signature of compilation spec -> in cache? -> directly return.


class JSONInputSpecEncoderForDebug(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return "<binary-content>"
        return json.JSONEncoder.default(self, obj)


input_spec_schema = {
    "compiler": {"type": "string", "allowed": AVAILABLE_LATEX_COMPILERS},
    "resources": {
        "type": "list",
        "required": True,
        "schema": {
            "type": "dict",
            # For now, we just check the keys.
            "keysrules": {
                "type": "string",
                "allowed": [
                    "url",
                    "file",
                    "git",
                    "tar",
                    "cache",
                    "content",
                    "main",
                    "path",
                ],
            },
        },
    },
    "options": {
        "type": "dict",
        "schema": {
            "bibliography": {
                "type": "dict",
                "schema": {
                    "command": {
                        "type": "string",
                        "allowed": AVAILABLE_BIBLIOGRAPHY_COMMANDS,
                    }
                },
            }
        },
    },
}
input_spec_validator = cerberus.Validator(input_spec_schema)


@builds_app.route("/sync", methods=["GET", "POST"])
def compiler_latex():
    input_spec = None

    # TODO Allows mixed APIs?
    # for eg. using GET/param to specify the compiler
    # with a POST/json payload (POST:/builds/sync?compiler=xelatex)

    input_spec_mode = None
    # Support for GET querystring requests.
    if request.method == "GET":
        input_spec_mode = "querystring"
        logger.info(pprint.pformat(request.args.to_dict(False)))
        input_spec, error = parse_querystring_resources_spec(
            request.args.to_dict(True), request.args.to_dict(False)
        )
        if error:
            return error, 400

    # Support for multipart/form-data requests.
    if request.content_type and "multipart/form-data" in request.content_type:
        input_spec_mode = "multipart/form-data"
        logger.info(request.content_type)
        logger.info(pprint.pformat(request.files))
        logger.info(pprint.pformat(request.form))
        input_spec, error = parse_multipart_resources_spec(request.form, request.files)
        if error:
            return error, 400

    if not input_spec:
        input_spec_mode = "json"
        input_spec, error = parse_json_resources_spec(request.get_json())
        if error:
            return error, 400

    if not input_spec:
        return {"error": "MISSING_COMPILATION_SPECIFICATION"}, 400

    # Payload validations.
    logger.info(request.content_type)
    logger.info(pprint.pformat(request.files))
    logger.info(pprint.pformat(request.form))
    logger.info(input_spec)

    if not input_spec_validator.validate(input_spec):
        return (
            json.dumps(
                {
                    "error": "INVALID_PAYLOAD_SHAPE",
                    "shape_errors": input_spec_validator.errors,
                    "input_spec_mode": input_spec_mode,
                    "input_spec": input_spec,
                },
                cls=JSONInputSpecEncoderForDebug,
            ),
            400,
            {"Content-Type": "application/json"},
        )

    # High-level normalizsation.
    logger.info(
        "Before normalization %s",
        pprint.pformat(prune_resources_content_for_logging(input_spec)),
    )

    # - compiler
    # Choose compiler: latex, pdflatex, xelatex or lualatex
    # We default to pdflatex.
    compilerName = input_spec.get("compiler", "pdflatex")

    # -options.bibliography.command
    # Choose bibliography command: bibtex, biber.
    # We default to bibtex.
    glom.assign(
        input_spec,
        "options.bibliography.command",
        glom.glom(input_spec, "options.bibliography.command", default="bibtex"),
        missing=dict,
    )

    # Pre-normalized data checks.

    # - resources (mandatory, must be an array).
    if not "resources" in input_spec:
        return {"error": "MISSING_RESOURCES"}, 400
    if type(input_spec["resources"]) != list:
        return {"error": "RESOURCES_SPEC_MUST_BE_A_LIST"}, 400

    # - compiler
    if compilerName not in AVAILABLE_LATEX_COMPILERS:
        return (
            {
                "error": "INVALID_COMPILER",
                "available_compilers": AVAILABLE_LATEX_COMPILERS,
            },
            400,
        )

    # -options.bibliography.command
    if (
        glom.glom(input_spec, "options.bibliography.command")
        not in AVAILABLE_BIBLIOGRAPHY_COMMANDS
    ):
        return (
            {
                "error": "INVALID_BILIOGRAPHY_COMMAND",
                "available_commands": AVAILABLE_BIBLIOGRAPHY_COMMANDS,
            },
            400,
        )

    # -------------
    # Pre-fetch normalization and checks.
    # -------------

    normalized_resources = normalize_resources_input(input_spec["resources"])
    # if logger.isEnabledFor(logging.DEBUG):
    #     logger.debug(pprint.pformat(normalized_resources))
    # - Prefetch checks (paths, main document, ...);
    errors = check_resources_prefetch(normalized_resources)
    if errors:
        return errors[0], 400

    # -------------
    # Fetching, post-fetch normalization and checks, filesystem creation.
    # -------------

    workspace_id = create_workspace(normalized_resources)
    error_in_try_block = None
    error_compilation = None

    try:

        def on_fetched(resource, data):
            logger.debug("Fetched %s: %s bytes", resource["build_path"], len(data))
            # Hash fetched inputs;
            resource["data_spec"] = process_resource_data_spec(data)
            error = persist_resource_to_workspace(workspace_id, resource, data)
            if error:
                return error
            # Input cache forwarding.
            is_ok, cache_response = forward_resource_to_cache(resource, data)
            if not is_ok or cache_response:
                return cache_response

        # Input cache provider.
        error = fetch_resources(
            normalized_resources, on_fetched, get_from_cache=get_resource_from_cache
        )
        if error:
            return error, 400
        # TODO
        # - Process build global signature/hash (compiler, resource hashes, other options...)

        # -------------
        # Compilation.
        # -------------

        # TODO Do an util to get main resource.
        main_resource = next(
            resource
            for resource in normalized_resources
            if resource["is_main_document"]
        )
        latexToPdfOutput = latexToPdf(
            compilerName,
            get_workspace_root_path(workspace_id),
            main_resource,
            input_spec["options"],
        )

        # -------------
        # Response creation.
        # -------------

        if not latexToPdfOutput["pdf"]:
            error_compilation = latexToPdfOutput["logs"]
            return (
                {"error": "COMPILATION_ERROR", "logs": latexToPdfOutput["logs"]},
                400,
            )
        # TODO Also return compilation logs here.
        # (So return a json. Include the PDF as base64 data?)
        # (In the long term it will be better to give a static URL to download
        # the generated PDF. We begin to talk about caching. This requires
        # lifecycle management. With something like a Redis.)
        # URL to get build result: PDF output, log, etc.
        # TODO In async / build status endpoint, returns:
        # - Normalized inputs;
        # - URLs for PDF output, log;

        # TODO Output cache management.

        return (
            latexToPdfOutput["pdf"],
            201,
            {
                "Content-Type": "application/pdf",
                # TODO Pass an option for returning as attachment (instead of inline, which is the default).
                "Content-Disposition": "inline;filename={}".format(
                    latexToPdfOutput["output_path"]
                ),
            },
        )

    except Exception as e:
        # -------------
        # Error management.
        # -------------

        # TODO Report error to Sentry (create a hook for custom code?).

        error_in_try_block = e
        logger.exception(e)
        return ({"error": "SERVER_ERROR"}, 500)

    finally:
        # -------------
        # Cleanup.
        # -------------

        # TODO Option to let workspace on failure
        # from env.
        if KEEP_WORKSPACE_DIR is False and (
            KEEP_WORKSPACE_DIR_ON_ERROR is False
            or (error_in_try_block is None and error_compilation is None)
        ):
            remove_workspace(workspace_id)
