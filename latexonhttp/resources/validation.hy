#! /usr/bin/env hy
"""
    latexonhttp.filesystem.resources
    ~~~~~~~~~~~~~~~~~~~~~
    Latex-On-HTTP filesystem resources management:
    process normalized resource input representation,
    to be used in actual filesystem implementation
    and caching mechanisms.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
(import [
    latexonhttp.utils.fun [fun-count-pred get-default all-pred]
])

(defn count-main-documents [resources]
    (fun-count-pred resources (fn [resource] (get-default resource "is-main-document" False))))

(defn has-path [resource]
    (get-default resource "build-path" None))

(defn add-error [errors error-name]
    (.append errors error-name)
    errors)

(defn check-resources-prefetch [resources]
    (setv errors [])
    (setv main-documents-occ (count-main-documents resources))
    ; Has a main document/resource;
    (if (< main-documents-occ 1)
        (add-error errors "MUST_SPECIFY_MAIN_DOCUMENT"))
    (if (> main-documents-occ 1)
        (add-error errors "MORE_THAN_ONE_MAIN_DOCUMENT"))
    ; All resources have a path (main document path has been normalized).
    (if-not (all-pred resources has-path)
        (add-error errors "MISSING_PATH_ON_RESOURCE"))
    errors)
