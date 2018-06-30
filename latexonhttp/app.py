# -*- coding: utf-8 -*-
"""
    latexonhttp.app
    ~~~~~~~~~~~~~~~~~~~~~
    Server application for Latex On HTTP API.
    Here are exposed the Rest API endpoints.

    :copyright: (c) 2017-2018 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import uuid
import urllib.request
import os.path
import base64
from fclist import fclist
from flask import Flask, request, jsonify, redirect, Response
from latexonhttp.compiler import latexToPdf

app = Flask(__name__)

# xelatex -output-directory /root/latex/ /root/latex/sample.tex


def is_safe_path(basedir, path, follow_symlinks=False):
    # resolves symbolic links
    if follow_symlinks:
        return os.path.realpath(path).startswith(basedir)
    return os.path.abspath(path).startswith(basedir)


@app.route("/")
def hello():
    # TODO Distribute documentation. (HTML)
    # TODO Add endpoints links / HATEOAS.
    return (
        jsonify(
            {
                "message": "Welcome to the Latex on HTTP API",
                "source": "https://github.com/YtoTech/latex-on-http",
            }
        ),
        200,
    )


# TODO Only register request here, and allows to define an hook for when
# the work is done?
# Allows the two? (async, sync)
@app.route("/compilers/latex", methods=["POST"])
def compiler_latex():
    # TODO Distribute documentation. (HTML)
    payload = request.get_json()
    if not payload:
        return jsonify("MISSING_PAYLOAD"), 400
    # Choose compiler: latex, pdflatex, xelatex or lualatex
    # We default to lualatex.
    compilerName = "lualatex"
    # TODO Choose them directly from the method?
    if "compiler" in payload:
        if payload["compiler"] not in ["latex", "lualatex", "xelatex", "pdflatex"]:
            return jsonify("INVALID_COMPILER"), 400
        compilerName = payload["compiler"]
    if not "resources" in payload:
        return jsonify("MISSING_RESOURCES"), 400
    # TODO Must be an array.
    # Iterate on resources.
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
    return Response(
        latexToPdfOutput["pdf"],
        status="201",
        headers={"Content-Type": "application/pdf"},
    )


@app.route("/fonts", methods=["GET"])
def fonts_list():
    fonts = []
    for font in fclist():
        fonts.append({
            "family": font.family,
            "name": font.fullname,
            "styles": list(font.style)
        })
    # TODO Group by families?
    return (jsonify({ "fonts": fonts }), 200)
