"""
latexonhttp.api.builds
~~~~~~~~~~~~~~~~~~~~~
Manage Latex builds / compilations.

:copyright: (c) 2017-2026 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

import json
import logging
import os
import pprint
from datetime import UTC, datetime
from urllib.parse import quote

import cerberus
import envparse
import glom
from flask import Blueprint, g, request, url_for

from latexonhttp.caching.resources import (
    forward_resource_to_cache,
    get_resource_from_cache,
)
from latexonhttp.compiler import (
    AVAILABLE_LATEX_COMPILERS,
    latexToPdf,
)
from latexonhttp.db.jobs import create_job, update_job
from latexonhttp.quota import (
    check_quota,
    get_client_ip,
    quota_rejection,
    rate_limit_headers,
)
from latexonhttp.resources.fetching import fetch_resources
from latexonhttp.resources.json_api import parse_json_resources_spec
from latexonhttp.resources.multipart_api import parse_multipart_resources_spec
from latexonhttp.resources.normalization import normalize_resources_input
from latexonhttp.resources.querystring_api import parse_querystring_resources_spec
from latexonhttp.resources.utils import (
    compute_compilation_hash,
    get_main_resource,
    process_resource_data_spec,
    prune_resources_content_for_logging,
    sanitize_input_spec_for_job,
)
from latexonhttp.resources.validation import check_resources_prefetch
from latexonhttp.sandbox import SandboxUnavailable
from latexonhttp.sandbox_diagnostics import (
    report_sandbox_diagnostic,
    sandbox_unavailable_issue,
)
from latexonhttp.usage import new_usage, usage_scores
from latexonhttp.workspaces.filesystem import (
    get_workspace_root_path,
    persist_resource_to_workspace,
)
from latexonhttp.workspaces.lifecycle import create_workspace, remove_workspace

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
            "response": {
                "type": "dict",
                "schema": {
                    "log_files_on_failure": {
                        "type": ["boolean", "string", "integer"],
                    },
                    "commands": {
                        "type": ["boolean", "string", "integer"],
                    },
                },
            },
            "compiler": {
                "type": "dict",
                "schema": {
                    "halt_on_error": {
                        "type": ["boolean", "string", "integer"],
                    },
                    "silent": {
                        "type": ["boolean", "string", "integer"],
                    },
                    "bibliography": {
                        "type": ["boolean", "string", "integer"],
                    },
                    "shell_escape": {
                        "type": ["boolean", "string", "integer"],
                    },
                    "force": {
                        "type": ["boolean", "string", "integer"],
                    },
                },
            },
        },
    },
}
input_spec_validator = cerberus.Validator(input_spec_schema)

RESOURCE_SOURCE_FIELDS = ("url", "file", "git", "tar", "cache", "content")


def check_resource_source_fields(resources):
    """Reject ambiguous resources before normalization chooses a source."""
    for resource_index, resource in enumerate(resources):
        source_fields = [field for field in RESOURCE_SOURCE_FIELDS if field in resource]
        if len(source_fields) > 1:
            return {
                "error": "MULTIPLE_RESOURCE_SOURCES",
                "message": (
                    "Use only one source field per resource: "
                    "url, file, git, tar, cache or content."
                ),
                "resource_index": resource_index,
                "source_fields": source_fields,
            }
    return None


def build_content_disposition_header(output_path):
    """Build an ASCII-safe ``Content-Disposition`` header value for the PDF.

    The output filename echoes back the uploaded document name, which may
    contain non-ASCII characters (e.g. an uploaded ``Lab02-肖奕然.tex``).
    HTTP header values must stay printable ASCII (RFC 9110): gunicorn rejects
    the whole response with an InvalidHeader otherwise — after the compilation
    itself succeeded. Follow RFC 6266: quote the filename, and for non-ASCII
    names percent-encode it (RFC 5987 ``filename*=UTF-8''`` parameter), using
    the percent-encoded form as ASCII ``filename`` fallback.
    """
    filename = os.path.basename(output_path) if output_path else "output.pdf"
    try:
        filename.encode("ascii")
    except UnicodeEncodeError:
        encoded = quote(filename, safe="")
        return f"inline; filename=\"{encoded}\"; filename*=UTF-8''{encoded}"
    # Keep the header value printable ASCII (RFC 9110): replace control
    # characters, then escape for the quoted-string syntax (RFC 9110 §5.6.5).
    printable = "".join(char if " " <= char <= "~" else "_" for char in filename)
    escaped = printable.replace("\\", "\\\\").replace('"', '\\"')
    return f'inline; filename="{escaped}"'


def parse_bool_str_arg(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    return str(value).lower() in ["true", "1", "t"]


def _update_job_safely(job_id, **metadata):
    """Do not replace a completed compilation response because tracking failed."""
    try:
        update_job(job_id, **metadata)
    except Exception:
        logger.exception("Could not update compilation job %s", job_id)


def _fetched_resources_metadata(resources):
    fetched_resources = [resource for resource in resources if "data_spec" in resource]
    cache_hits = [
        resource for resource in fetched_resources if resource["type"] == "hash/cache"
    ]
    return {
        "fetched_resources_count": len(fetched_resources),
        "fetched_resources_size": sum(
            resource["data_spec"]["size"] for resource in fetched_resources
        ),
        "fetched_resources_cache_hits": len(cache_hits),
        "fetched_resources_cache_hits_size": sum(
            resource["data_spec"]["size"] for resource in cache_hits
        ),
    }


def get_rate_limit_documentation_url():
    """Absolute URL of the rate-limiting documentation served from /docs/."""
    forwarded_scheme = (
        (request.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip()
    )
    return (
        url_for("docs.documentation", _external=True, _scheme=forwarded_scheme or None)
        + "api/rate-limiting/"
    )


@builds_app.before_request
def enforce_build_quota():
    """Reject requests beyond the fair-use quota before parsing the payload.

    The decision is also stored on `g` so passing responses expose the
    rate-limit headers of their binding window.
    """
    decision = check_quota(get_client_ip(request))
    if decision is None:
        # Quota disabled, allowlisted client, or fail-open store failure.
        return
    g.quota_decision = decision
    if not decision["allowed"]:
        return quota_rejection(decision, get_rate_limit_documentation_url())


@builds_app.after_request
def expose_rate_limit_headers(response):
    decision = g.get("quota_decision")
    if decision:
        for name, value in rate_limit_headers(decision).items():
            response.headers[name] = value
    return response


@builds_app.after_request
def track_job_response(response):
    job_id = g.get("compilation_job_id")
    if not job_id or not g.get("compilation_job_created"):
        return response
    now = datetime.now(UTC)
    payload = response.get_json(silent=True)
    error_code = payload.get("error") if isinstance(payload, dict) else None
    metadata = {
        "job_status": "completed" if response.status_code == 201 else "errored",
        "error_code": (
            None if response.status_code == 201 else error_code or "SERVER_ERROR"
        ),
        "completed_at": now,
        "replied_at": now,
    }
    # Also close a phase interrupted by an exception rather than a normal return.
    fetched_metadata = _fetched_resources_metadata(g.compilation_job_resources)
    if g.get("compilation_job_stage") == "fetching":
        metadata.update(ended_fetch_at=now, **fetched_metadata)
    elif g.get("compilation_job_stage") == "compiling":
        metadata["ended_compiling_at"] = now
    # Usage scoring: measure the reply and close the record opened at
    # admission; a scoring failure must not take the job update down.
    try:
        outgoing_size = len(response.get_data())
        scores = usage_scores(g.compilation_usage, fetched_metadata, now, outgoing_size)
        metadata.update(
            response_size=outgoing_size,
            usage_score_incoming=scores["incoming"],
            usage_score_fetch=scores["fetch"],
            usage_score_processing=scores["processing"],
            usage_score_outgoing=scores["outgoing"],
            usage_score_total=scores["total"],
        )
    except Exception:
        logger.exception("Could not score usage of compilation job %s", job_id)
    _update_job_safely(job_id, **metadata)
    response.headers["X-Job-ID"] = job_id
    return response


@builds_app.route("/sync", methods=["GET", "POST"])
def compiler_latex():
    received_at = datetime.now(UTC)
    # Buffer before any parser consumes the body so every request has an exact
    # byte count, including multipart framing, and later parsers see the same data.
    http_payload_size = len(request.get_data(cache=True))
    # Usage scoring: open the record at admission; it is closed and persisted
    # with the job metadata at reply time (see track_job_response).
    g.compilation_usage = new_usage(received_at, http_payload_size)
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
    logger.info(pprint.pformat(prune_resources_content_for_logging(input_spec)))

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

    # -options.compiler.halt_on_error
    glom.assign(
        input_spec,
        "options.compiler.halt_on_error",
        parse_bool_str_arg(
            glom.glom(input_spec, "options.compiler.halt_on_error", default=False)
        ),
        missing=dict,
    )
    # -options.compiler.silent
    glom.assign(
        input_spec,
        "options.compiler.silent",
        parse_bool_str_arg(
            glom.glom(input_spec, "options.compiler.silent", default=False)
        ),
        missing=dict,
    )
    # -options.compiler.force
    glom.assign(
        input_spec,
        "options.compiler.force",
        parse_bool_str_arg(
            glom.glom(input_spec, "options.compiler.force", default=True)
        ),
        missing=dict,
    )
    # -options.compiler.bibliography
    glom.assign(
        input_spec,
        "options.compiler.bibliography",
        parse_bool_str_arg(
            glom.glom(input_spec, "options.compiler.bibliography", default=True)
        ),
        missing=dict,
    )
    # -options.compiler.shell_escape (for packages such as minted)
    glom.assign(
        input_spec,
        "options.compiler.shell_escape",
        parse_bool_str_arg(
            glom.glom(input_spec, "options.compiler.shell_escape", default=False)
        ),
        missing=dict,
    )
    # -options.response.log_files_on_failure
    glom.assign(
        input_spec,
        "options.response.log_files_on_failure",
        parse_bool_str_arg(
            glom.glom(input_spec, "options.response.log_files_on_failure", default=True)
        ),
        missing=dict,
    )
    # -options.response.commands
    glom.assign(
        input_spec,
        "options.response.commands",
        parse_bool_str_arg(
            glom.glom(input_spec, "options.response.commands", default=False)
        ),
        missing=dict,
    )

    # Pre-normalized data checks.

    # - resources (mandatory, must be an array).
    if "resources" not in input_spec:
        return {"error": "MISSING_RESOURCES"}, 400
    if type(input_spec["resources"]) is not list:
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

    # -------------
    # Pre-fetch normalization and checks.
    # -------------

    source_fields_error = check_resource_source_fields(input_spec["resources"])
    if source_fields_error:
        return source_fields_error, 400

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
    g.compilation_job_id = workspace_id
    g.compilation_job_created = False
    g.compilation_job_resources = normalized_resources
    error_in_try_block = None
    error_compilation = None

    try:
        create_job(
            {
                "id": workspace_id,
                "job_status": "received",
                "compiler": compilerName,
                "compilation_hash": None,
                "input_spec_mode": input_spec_mode,
                "http_payload_size": http_payload_size,
                "cleaned_payload": sanitize_input_spec_for_job(input_spec),
                "remote_ip": request.remote_addr,
                "forwarded_remote_ip": request.headers.get("X-Forwarded-For"),
                "user_agent": request.headers.get("User-Agent"),
                "received_at": received_at,
            }
        )
        g.compilation_job_created = True
        g.compilation_job_stage = "received"

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
            return None

        # Input cache provider.
        g.compilation_job_stage = "fetching"
        _update_job_safely(
            workspace_id,
            job_status="fetching",
            started_fetch_at=datetime.now(UTC),
        )
        error = fetch_resources(
            normalized_resources, on_fetched, get_from_cache=get_resource_from_cache
        )
        g.compilation_job_stage = "fetched"
        _update_job_safely(
            workspace_id,
            ended_fetch_at=datetime.now(UTC),
            **_fetched_resources_metadata(normalized_resources),
        )
        if error:
            return error, 400

        # -------------
        # Compilation.
        # -------------

        main_resource = get_main_resource(normalized_resources)
        g.compilation_job_stage = "compiling"
        _update_job_safely(
            workspace_id,
            job_status="compiling",
            compilation_hash=compute_compilation_hash(
                compilerName, input_spec["options"], normalized_resources
            ),
            started_compiling_at=datetime.now(UTC),
        )
        latexToPdfOutput = latexToPdf(
            compilerName,
            get_workspace_root_path(workspace_id),
            main_resource,
            workspace_id,
            input_spec["options"],
        )
        g.compilation_job_stage = "compiled"
        _update_job_safely(
            workspace_id,
            ended_compiling_at=datetime.now(UTC),
            output_type="pdf" if latexToPdfOutput["pdf"] is not None else None,
            output_size=(
                len(latexToPdfOutput["pdf"])
                if latexToPdfOutput["pdf"] is not None
                else None
            ),
        )

        # -------------
        # Response creation.
        # -------------

        if latexToPdfOutput["status"] == "error":
            error_compilation = latexToPdfOutput["logs"]
            return (
                {
                    **latexToPdfOutput["error"],
                    "duration": round(latexToPdfOutput["duration"], 2),
                    "logs": latexToPdfOutput["logs"],
                    **(
                        {
                            "log_files": latexToPdfOutput["log_files"],
                        }
                        if glom.glom(
                            input_spec, "options.response.log_files_on_failure"
                        )
                        else {}
                    ),
                    **(
                        {
                            "commands": latexToPdfOutput["commands"],
                        }
                        if glom.glom(input_spec, "options.response.commands")
                        else {}
                    ),
                },
                400,
            )
        if latexToPdfOutput["status"] != "ok":
            error_compilation = latexToPdfOutput["logs"]
            return (
                {
                    "error": (
                        "COMPILATION_TIMEOUT"
                        if latexToPdfOutput["is_timeout"]
                        else "COMPILATION_ERROR"
                    ),
                    "duration": round(latexToPdfOutput["duration"], 2),
                    "logs": latexToPdfOutput["logs"],
                    **(
                        {
                            "log_files": latexToPdfOutput["log_files"],
                        }
                        if glom.glom(
                            input_spec, "options.response.log_files_on_failure"
                        )
                        else {}
                    ),
                    **(
                        {
                            "commands": latexToPdfOutput["commands"],
                        }
                        if glom.glom(input_spec, "options.response.commands")
                        else {}
                    ),
                },
                400,
            )
        # TODO Also return compilation logs here.
        # (So return a json. Include the PDF as base64 data?)
        #  -> Yes, but as an option.
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
                # TODO Pass an option for returning as attachment (instead of the
                # default, inline).
                "Content-Disposition": build_content_disposition_header(
                    latexToPdfOutput["output_path"]
                ),
            },
        )

    except SandboxUnavailable as error:
        # Never fall back to executing untrusted TeX without the sandbox.
        logger.error("Compilation sandbox unavailable: %s", error)
        report_sandbox_diagnostic(
            sandbox_unavailable_issue(error),
            command=[compilerName],
            directory=get_workspace_root_path(workspace_id),
            compiler=compilerName,
        )
        return {"error": "SANDBOX_UNAVAILABLE"}, 503

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

        # Option to let workspace on failure
        # from env.
        if KEEP_WORKSPACE_DIR is False and (
            KEEP_WORKSPACE_DIR_ON_ERROR is False
            or (error_in_try_block is None and error_compilation is None)
        ):
            remove_workspace(workspace_id)
