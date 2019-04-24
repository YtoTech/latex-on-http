#! /usr/bin/env hy
"""
    latexonhttp.caching.resources
    ~~~~~~~~~~~~~~~~~~~~~
    Managing input resources caching.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
(import logging)
(import datetime)
(import [
    latexonhttp.utils.fun [get-default fun-merge-dicts fun-dict-update fun-dict-remove-key]
])
(import [
    latexonhttp.caching.store [get-cache-metadata persist-cache-metadata]
])
(import [
    latexonhttp.caching.filesystem [apply-cache-action]
])

(setv logger (.getLogger logging __name__))

; 3 Ko.
(setv MIN-FILE-SIZE-CACHE-THRESHOLD (* 3 1000))
; 200 Mo.
(setv MAX-RESOURCES-CACHE-SIZE (* 200 1000000))

; # Cache module:
; # - Create directory for caching files (delete on start / if no metadata);
; # - Put input files on cache directory, with metadata (size, cache id: flat directory);
; # - Check input cache metadata for enforcing constraints (max size cache), act if needed (delete files on overflow);
; # - Actually take the metadata, the resource forwared and return the actions: add/rm, rm --all;
; # - From time to time, as a sanity check, get directory size to check that it matches our metadata.

; TODO /caches/resources endpoint

; --------------------------------
; External API.
; --------------------------------

; TODO Actually the caching must be forwarded to a decicated process
; for the whole node to ensure consistency.
; Also will avoid cache management overhead in main process.
; --> Uses a zeroMQ socket as the API.
; The cache layer could then be 100% independent.
; For eg. could be implemented in Go, with a mixed
; in-memory and on-disk cache.
; There could be a memcached adapter, to rely on existing
; caching technology.
; With enough data, there could be neural-network trained
; to optimized bandwidth-saving cache hits.

(defn forward-resource-to-cache [resource data]
    (setv cache-metadata (get-cache-metadata))
    ; TODO Maintain metrics on resource usage, for eg:
    ; - resources inputs for last 24 hours;
    ; - last N (10000) resources inputs.
    ; With this data + hit logs, we could process cache efficiency metrics.
    ; TODO Logs this data and create datasets, so we can try strategies and
    ; see which ones work best on past-data.
    (setv actions (+
        ; - Check/Init resource cache -> actions;
        (prepare-cache cache-metadata)
        ; - Decide what to do with current resource -> actions;
        (process-resource-caching-decision cache-metadata resource data)
    ))
    ; (logger.debug "Cache actions: %s" actions)
    (for [action actions]
        ; - Apply actions;
        ; TODO Normalize action using map-resource-for-cache-metadata?
        (apply-cache-action action)
        ; - Update cache metadata after actions.
        ; Update cache metadata after each action,
        ; so we have an as much as possible up-to-date cache
        ; for multi-threading/process context.
        ; (See comment above on making it a dedicated and concurrent-safe process)
        (setv cache-metadata (persist-cache-metadata (update-cache-metadata-for-action cache-metadata action))))
    )

; TODO Cache usage.
; Maintain statistics on cache hits,
; with volumes of input resource bandwitdh hit/missed.

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

(defn process-resource-caching-decision [cache-metadata resource data]
    ; Naive FIFO cache:
    ; - Check if already cached;
    ; - Check for a caching size threshold;
    ; - (If threshold passed) add to cache;
    ; - Remove from cache if max cache size reached (remove older cache entries).
    ; TODO Uses resources stats to cache the most used resources.
    (if (>= (get resource "data_spec" "size") MIN-FILE-SIZE-CACHE-THRESHOLD)
      [
        {
          "name" "add_resource"
          "resource" resource
          "data" data
        }
      ]
      []))

; --------------------------------
; Cache updates.
; --------------------------------

(defn generate-cache-timestamp []
  (.isoformat (.now datetime.datetime)))

(defn init-cache-metadata []
    {
        "last_updated_at" (generate-cache-timestamp)
        "total_size" 0
        "cached_resources" {}
    })

(defn process-cache-total-size [resources]
  (sum (map
    (fn [resource] (get resource "size"))
    resources)))

(defn update-cache-metadata-metrics [cache-metadata]
  (fun-merge-dicts [
    cache-metadata
    {
      "total_size" (process-cache-total-size (.values (get cache-metadata "cached_resources")))
      "last_updated_at" (generate-cache-timestamp)
    }
  ]))

(defn map-resource-for-cache-metadata [resource]
  (setv resource-hash (get resource "data_spec" "hash"))
  {
    resource-hash {
      "size" (get resource "data_spec" "size")
      "hash" resource-hash
      "added_at" (generate-cache-timestamp)
    }
  })

(defn add-resource-to-cache-metadata [cache-metadata resource]
  (update-cache-metadata-metrics
    (fun-merge-dicts [
      cache-metadata
      {
        ; This mutate original cached_resources dict.
        "cached_resources" (fun-dict-update (get cache-metadata "cached_resources") (map-resource-for-cache-metadata resource))
      }
    ])))


(defn remove-resource-from-cache-metadata [cache-metadata resource]
  (update-cache-metadata-metrics
    (fun-merge-dicts [
      cache-metadata
      {
        ; This mutate original cached_resources dict.
        "cached_resources" (fun-dict-remove-key (get cache-metadata "cached_resources") (get resource "data_spec" "hash"))
      }
    ])))

(defn update-cache-metadata-for-action [cache-metadata action]
  (setv action-name (get action "name"))
  (cond
    [(= action-name "reset_cache")
      (init-cache-metadata)]
    [(= action-name "add_resource")
      (add-resource-to-cache-metadata cache-metadata (get action "resource"))]
    [(= action-name "remove_resource")
      (remove-resource-from-cache-metadata cache-metadata (get action "resource"))]
    [True
      (raise (RuntimeError (.format "Unsupported cache action '{}'" action-name)))]
  ))
