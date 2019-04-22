#! /usr/bin/env hy
"""
    latexonhttp.resources.validation
    ~~~~~~~~~~~~~~~~~~~~~
    Latex-On-HTTP input resource validation.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
(import [
    latexonhttp.utils.fun [fun-count-pred get-default all-pred]
])

(defn count-main-documents [resources]
    (fun-count-pred resources (fn [resource] (get-default resource "is_main_document" False))))

(defn has-path [resource]
    (get-default resource "build_path" None))

(defn add-error [errors error-name]
    (.append errors error-name)
    errors)

; TODO Function to allows to compose validation.
; (defn apply-checks [resources checks &optional [fail-fast True]]
;     ; TODO Apply sequentially all check functions;
;     ; TODO Allows for "shared" variables (eg. main-documents-occ): macro?
;     ; TODO On fail-fast, stop and return on first check failure.
;     )

; (apply-checks
;     resources
;     [
;         (setv main-documents-occ (count-main-documents resources))
;         (fn [] (if (< main-documents-occ 1)
;             (add-error errors "MUST_SPECIFY_MAIN_DOCUMENT")))
;     ])

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
