# -*- coding: utf-8 -*-
"""
    latexonhttp.resources.multipart_api
    ~~~~~~~~~~~~~~~~~~~~~
    HTTP multipart/form-data API for compilation resources specification.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import logging
import json
import base64
import pprint
import glom

logger = logging.getLogger(__name__)


def construct_resources_specification_from_files(multipart_files):
    # We make the following hypothesis:
    # - main Latex document is the first file with the .tex extension;
    # - if no file with .tex extension but only one file, it is considered to be the main Latex document;
    # - other files are considered (non-main-document) resources;
    # - all resources path is their multipart file name.
    if len(multipart_files) < 1:
        return None, {"error": "EXPECTING_AT_LEAST_ONE_MULTIPART_FILE"}
    first_tex_file = next(
        (
            multipart_file
            for multipart_file in multipart_files.values()
            if ".tex" in multipart_file.filename
        ),
        None,
    )
    if not first_tex_file:
        if len(multipart_files) != 1:
            return (
                None,
                {"error": "UNABLE_TO_IDENTIFY_MAIN_DOCUMENT_IN_MULTIPART_FILES"},
            )
        first_tex_file = next(multipart_files.values())
    resources_spec = []
    for multipart_key, multipart_file in multipart_files.items():
        resource_spec = {
            "multipart": multipart_key,
        }
        if multipart_file == first_tex_file:
            resource_spec["main"] = True
        resources_spec.append(resource_spec)
    return resources_spec, None


def parse_multipart_resources_spec(forms, files):
    json_spec = {}
    # Loads options.
    if "compiler" in forms:
        json_spec["compiler"] = forms["compiler"]

    # options. entries.
    for option_key in (param_key for param_key in forms if "options." in param_key):
        glom.assign(json_spec, option_key, forms[option_key], missing=dict)

    # Get resources specification.
    if "resources" in forms:
        try:
            json_spec["resources"] = json.loads(forms["resources"])
        except json.decoder.JSONDecodeError as jde:
            return (
                None,
                {
                    "error": "INVALID_RESOURCES_JSON",
                    "exception_content": str(jde),
                },
            )
    else:
        # TODO Else reconstruct resources spec with best guest:
        # one main tex file, with other non tex resources.
        # Replace files in resource spec by uploaded multipart files.
        json_spec["resources"], error = construct_resources_specification_from_files(
            files
        )
        if error:
            return None, error
        logger.info(
            "Reconstructed resource spec: %s", pprint.pformat(json_spec["resources"])
        )
    for resource in json_spec["resources"]:
        if "multipart" not in resource:
            continue
        # Does an uploaded file match?
        if resource["multipart"] not in files:
            return (
                None,
                {"error": "MISSING_MULTIPART_FILE", "filename": resource["multipart"]},
            )
        multipart_file = files[resource["multipart"]]
        # We uses base64 for encoding file content.
        resource["file"] = base64.b64encode(multipart_file.read())
        # We can delete the "multipart" entry in the spec,
        # to keep it normalized.
        del resource["multipart"]
        if "path" not in resource:
            resource["path"] = multipart_file.filename
    return json_spec, None
