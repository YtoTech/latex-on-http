# -*- coding: utf-8 -*-
"""
    latexonhttp.resources.multipart_api
    ~~~~~~~~~~~~~~~~~~~~~
    HTTP multipart/form-data API for compilation resources specification.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import json
import base64


def parse_multipart_resources_spec(forms, files):
    json_spec = {}
    # Loads options.
    if "compiler" in forms:
        json_spec["compiler"] = forms["compiler"]
    # Get resources specification.
    if "resources" in forms:
        # TODO Handle invalid json.
        json_spec["resources"] = json.loads(forms["resources"])
    # TODO Else reconstruct resources spec with best guest:
    # only one main tex file, with other non tex resources.
    # Replace files in resource spec by uploaded multipart files.
    for resource in json_spec["resources"]:
        if "multipart" not in resource:
            continue
        # Does an uploaded file match?
        if resource["multipart"] not in files:
            return (
                None,
                {"error": "MISSING_MULTIPART_FILE", "filename": resource["multipart"]},
            )
        uploaded_file = files[resource["multipart"]]
        # We uses base64 for encoding file content.
        resource["file"] = base64.b64encode(uploaded_file.read())
        if "path" not in resource:
            resource["path"] = uploaded_file.filename
    return json_spec, None
