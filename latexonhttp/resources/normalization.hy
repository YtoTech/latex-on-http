#! /usr/bin/env hy
"""
    latexonhttp.resources.normalization
    ~~~~~~~~~~~~~~~~~~~~~
    LaTeX-On-HTTP resources input normalization:
    process normalized resource input representation,
    to be used in actual filesystem implementation
    and caching mechanisms.

    :copyright: (c) 2019-2022 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
(import
    latexonhttp.utils.fun [fun-sort get-default])

; --------------------------------------------
; Prefetch resource normalizsation.
; --------------------------------------------

(defn normalize-resources-input [resources]
    (sort-resources (list (map
        (fn [resource] (normalize-resource-input resource resources))
        resources
    ))))

(defn normalize-resource-input [resource resources]
    """
    Normalize the resource input, without performing any operation
    or checks.
    """
    ; TODO Do not use setv, but make intermediate normalized "passes"?
    (setv resource-type (get-resource-type resource))
    (setv is-main-document (is-resource-main-document resource resources))
    {
        "type" resource-type
        ; TODO Under build key? (for is-main-document, build-path)
        "is_main_document" is-main-document
        "build_path" (normalized-resource-build-path resource is-main-document)
        "output_path" (normalized-resource-output-path resource is-main-document)
        "body_source" (get-body-source resource resource-type)
    })

(defn get-resource-type [resource]
    (cond
        (in "url" resource) "url/file"
        (in "file" resource) "base64/file"
        (in "git" resource) "url/git"
        (in "tar" resource) "url/tar"
        (in "cache" resource) "hash/cache"
        (in "content" resource) "utf8/string"
        ; TODO How to support multi-part data for passing tar, file, zip, git, etc. in HTTP request body?
        True "unknow"
    ))

(defn get-body-source [resource resource-type]
    (cond
        (= resource-type "url/file")
            {
                "url" (get resource "url")
            }
        (= resource-type "base64/file")
            {
                "raw_base64" (get resource "file")
            }
        (= resource-type "url/git")
            {
                "url" (get resource "git")
            }
        (= resource-type "url/tar")
            {
                "url" (get resource "tar")
            }
        (= resource-type "hash/cache")
            {
                "hash" (get resource "cache")
            }
        (= resource-type "utf8/string")
            {
                "raw_string" (get resource "content")
            }
    ))

(defn is-resource-main-document [resource resources]
    (if (= (len resources) 1)
        True
        (get-default resource "main" False)))

(defn normalized-resource-build-path [resource is-main-document]
    (if is-main-document
        "__main_document__.tex"
        (get-default resource "path" None)))

(defn normalized-resource-output-pathname [path-name]
  (.replace path-name ".tex" ".pdf"))

(defn normalized-resource-output-path [resource is-main-document]
    (if is-main-document
        (normalized-resource-output-pathname (get-default resource "path" "output.pdf"))
        None))

(defn sort-resources [resources]
    (fun-sort
        resources
        (fn [resource]
            (setv build-path (get resource "build_path"))
            (if build-path build-path ""))))
