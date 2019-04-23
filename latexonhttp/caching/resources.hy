#! /usr/bin/env hy
"""
    latexonhttp.caching.resources
    ~~~~~~~~~~~~~~~~~~~~~
    Managing input resources caching.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
(import logging)
(import [
    latexonhttp.utils.fun [get-default]
])
(import [
    latexonhttp.caching.store [get-cache-metadata]
])
(import [
    latexonhttp.caching.filesystem [apply-cache-actions]
])

(setv logger (.getLogger logging __name__))


; # Cache module:
; # - Create directory for caching files (delete on start / if no metadata);
; # - Put input files on cache directory, with metadata (size, cache id: flat directory);
; # - Check input cache metadata for enforcing constraints (max size cache), act if needed (delete files on overflow);
; # - Actually take the metadata, the resource forwared and return the actions: add/rm, rm --all;
; # - From time to time, as a sanity check, get directory size to check that it matches our metadata.

; --------------------------------
; External API.
; --------------------------------

(defn forward-resource-to-cache [resource data]
    (setv cache-metadata (get-cache-metadata))
    (setv actions (+
        ; - Check/Init resource cache -> actions;
        (prepare-cache cache-metadata)
        ; - Decide what to do with current resource -> actions;
        (process-resource-caching-decision cache-metadata resource)
    ))
    (logger.debug "Cache actions: %s" actions)
    ; - Apply actions;
    ; TODO Update cache metadata after each action?
    ; --> So we have an as much as possible up-to-date cache
    ; for multi-threading/process context.
    ; TODO Actually the caching must be forwarded to a decicated process
    ; for the whole node to ensure consistency.
    ; Also will avoid cache management overhead in main process.
    ; --> Uses a zeroMQ socket as the API.
    ; The cache layer could then be 100% independent.
    (apply-cache-actions actions)
    ; TODO
    ; - Update cache metadata after actions.
    )

; --------------------------------
; Decision making.
; --------------------------------

(defn prepare-cache [cache-metadata]
    (if (get-default cache-metadata "last_updated_at")
        []
        [
            {
                "name" "reset_cache"
            }
        ]))

(defn process-resource-caching-decision [cache-metadata resource]
    [])

; --------------------------------
; Cache updates.
; --------------------------------

; TODO
; last_updated_at
; total_size

(defn update-cache-for-action [cache-metadata action]
    ; TODO cond
    ; reset_all -> init_cache_metadata;
    ; add -> add resource to cache, update global metrics;
    ; remove -> remove resource from cache, update global metrics.
    None)
