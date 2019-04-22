#! /usr/bin/env hy
"""
    latexonhttp.resources.normalization
    ~~~~~~~~~~~~~~~~~~~~~
    Latex-On-HTTP resources input normalization:
    process normalized resource input representation,
    to be used in actual filesystem implementation
    and caching mechanisms.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
(import [
    latexonhttp.utils.fun [fun-sort get-default]
])

; # TODO Extract the filesystem management in a module:
; # - determine of fs/files actions to get to construct the filesystem;
; #   - support content/string, base64/file, url/file, url/git, url/tar, post-data/tar
; # - hash and make a (deterministic) signature of files uploaded;
; # - from the list of actions, prepare the file system (giving only a root directory);
; # (- add a cache management on the file system preparation subpart).
; #
; # The compiler only uses:
; # - the hash for an eventual output cache
; # (if entire input signature match a cached output file, just return this file);
; # - the prepared directory of files where the build happens.
; 
; Persist cached files.
; Endpoint for checking if inputs (or output) are cached,
; for smart client use.

; # Do it in Hy.


; mainResource = None
; workspaceId = str(uuid.uuid4())
; workspacePath = os.path.abspath("./tmp/" + workspaceId)
; for resource in payload["resources"]:
;     # Must have:
;     # Either data or url.
;     if "main" in resource and resource["main"] is True:
;         mainResource = resource
;     # TODO Be immutable and preserve the original content payload.
;     if "url" in resource:
;         # Fetch and put in resource content.
;         # TODO Handle errors (404, network, etc.).
;         print("Fetching {} ...".format(resource["url"]))
;         resource["content"] = urllib.request.urlopen(resource["url"]).read()
;         # Decode if main file?
;         if "main" in resource and resource["main"] is True:
;             resource["content"] = resource["content"].decode("utf-8")
;     if "file" in resource:
;         resource["content"] = base64.b64decode(resource["file"])
;     if not "content" in resource:
;         return jsonify("MISSING_CONTENT"), 400
;     # Path relative to the project.
;     if "path" in resource:
;         # Write file to workspace, if not the main file.
;         if not "main" in resource or resource["main"] is not True:
;             # https://security.openstack.org/guidelines/dg_using-file-paths.html
;             resource["path"] = os.path.abspath(
;                 workspacePath + "/" + resource["path"]
;             )
;             if not is_safe_path(workspacePath, resource["path"]):
;                 return jsonify("INVALID_PATH"), 400
;             print("Writing to {} ...".format(resource["path"]))
;             os.makedirs(os.path.dirname(resource["path"]), exist_ok=True)
;             if not "url" in resource and not "file" in resource:
;                 resource["content"] = resource["content"].encode("utf-8")
;             with open(resource["path"], "wb") as f:
;                 f.write(resource["content"])
; # TODO If more than one resource, must give a main file flag.
; if len(payload["resources"]) == 1:
;     mainResource = payload["resources"][0]
; else:
;     if not mainResource:
;         return jsonify("MUST_SPECIFY_MAIN_RESOURCE"), 400


(defn normalize-resources-input [resources]
    (sort-resources (list (map normalize-resource-input resources))))

(defn normalize-resource-input [resource]
    """
    Normalize the resource input, without performing any operation
    or checks.
    """
    ; TODO Do not use setv, but make intermediate normalized "passes"?
    (setv resource-type (get-resource-type resource))
    (setv is-main-document (is-resource-main-document resource))
    {
        "type" resource-type
        ; TODO Under build key? (for is-main-document, build-path)
        "is-main-document" is-main-document
        "build-path" (normalized-resource-build-path resource is-main-document)
        "body-source" (get-body-source resource resource-type)
    })

(defn get-resource-type [resource]
    (cond
        [(in "url" resource) "url/file"]
        [(in "file" resource) "base64/file"]
        [(in "git" resource) "url/git"]
        [(in "tar" resource) "url/tar"]
        [(in "cache" resource) "hash/cache"]
        [(in "content" resource) "utf8/string"]
        ; TODO How to support multi-part data for passing tar, file, zip, git, etc. in HTTP request body?
        [True "unknow"]
    ))

(defn get-body-source [resource resource-type]
    (cond
        [(= resource-type "url/file")
            {
                "url" (get resource "url")
            }]
        [(= resource-type "base64/file")
            {
                "raw-base64" (get resource "file")
            }]
        [(= resource-type "url/git")
            {
                "url" (get resource "git")
            }]
        [(= resource-type "url/tar")
            {
                "url" (get resource "tar")
            }]
        [(= resource-type "hash/cache")
            {
                "hash" (get resource "cache")
            }]
        [(= resource-type "utf8/string")
            {
                "raw-string" (get resource "content")
            }]
    ))

(defn is-resource-main-document [resource]
    (get-default resource "main" False))

(defn normalized-resource-build-path [resource is-main-document]
    (if is-main-document
        "__main_document__.tex"
        (get-default resource "path" None)))

(defn sort-resources [resources]
    (fun-sort
        resources
        (fn [resource]
            (setv build-path (get resource "build-path"))
            (if build-path build-path ""))))
