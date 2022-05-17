# -*- coding: utf-8 -*-
"""
    latexonhttp.resources.querystring_api
    ~~~~~~~~~~~~~~~~~~~~~
    HTTP GET querystring API for compilation resources specification.

    :copyright: (c) 2020 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import logging
import json
import base64
import pprint
import glom

logger = logging.getLogger(__name__)

RESOURCE_TYPE_TO_VALUE_KEY = {
    "url": "url",
    "file": "file",
    "base64": "file",
    "content": "content",
    "string": "content",
}


def smart_guess_resource_type(resource_value, _resource_path):
    if type(resource_value) == str and resource_value.startswith("http"):
        return "url"
    return "content"


def parse_querystring_resources_spec(params, multi_params):
    json_spec = {}
    # Loads options.
    if "compiler" in params:
        json_spec["compiler"] = params["compiler"]

    # options. entries.
    for option_key in (param_key for param_key in params if "options." in param_key):
        glom.assign(json_spec, option_key, params[option_key], missing=dict)

    # List-based resource specification.
    other_resources = []
    if "resource-value[]" in multi_params:
        resources_value = multi_params["resource-value[]"]
        # We must have resources path.
        if "resource-path[]" not in multi_params:
            return (
                None,
                {"error": "MISSING_RESOURCES_PATH"},
            )
        resources_path = multi_params["resource-path[]"]
        resources_type = (
            multi_params["resource-type[]"]
            if "resource-type[]" in multi_params
            else [None] * len(resources_value)
        )
        # We must have same length path and type specs.
        if not all(
            list_len == len(resources_value)
            for list_len in [
                len(resources_value),
                len(resources_path),
                len(resources_type),
            ]
        ):
            return (
                None,
                {"error": "RESOURCES_SPEC_MUST_BE_OF_SAME_LENGTH"},
            )

        for resource_type, resource_path, resource_value in zip(
            resources_type, resources_path, resources_value
        ):
            # If no resource types specified, try smart guess (content or URL).
            actual_resource_type = (
                resource_type
                if resource_type
                else smart_guess_resource_type(resource_value, resource_path)
            )
            if actual_resource_type not in RESOURCE_TYPE_TO_VALUE_KEY:
                return (
                    None,
                    {
                        "error": "INVALID_RESOURCE_TYPE",
                        "value": actual_resource_type,
                        "supported_resource_types": RESOURCE_TYPE_TO_VALUE_KEY.keys(),
                    },
                )
            value_key = RESOURCE_TYPE_TO_VALUE_KEY[actual_resource_type]
            other_resources.append(
                {
                    value_key: resource_value,
                    "path": resource_path,
                }
            )

    # Indexed-based resources specification.
    if "resource-value[0]" in params:
        # TODO
        pass

    main_resource = []
    if "content" in params:
        main_resource = [{"content": params["content"], "main": True}]
    if "url" in params:
        main_resource = [{"url": params["url"], "main": True}]
    if "file" in params:
        main_resource = [{"file": params["file"], "main": True}]

    json_spec["resources"] = main_resource + other_resources

    logger.info(pprint.pformat(json_spec))

    return json_spec, None
