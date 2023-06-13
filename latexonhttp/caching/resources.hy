#! /usr/bin/env hy
"""
    latexonhttp.caching.resources
    ~~~~~~~~~~~~~~~~~~~~~
    Managing input resources caching.

    :copyright: (c) 2019-2022 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
(import logging)
(import datetime)
(import
    latexonhttp.utils.fun [get-default fun-merge-dicts fun-dict-update fun-dict-remove-key fun-sort])
(import
    latexonhttp.caching.store [get-cache-metadata persist-cache-metadata])
(import
    latexonhttp.caching.filesystem [apply-cache-action get-cached-data apply-sanity-check MAX-RESOURCES-CACHE-SIZE ENABLE-SANITY-CHECKS])
(import
    latexonhttp.caching.bridge [request-cache-process-async request-cache-process-sync])

(setv logger (.getLogger logging __name__))

; 3 Ko.
(setv MIN-FILE-SIZE-CACHE-THRESHOLD (* 3 1000))


; --------------------------------
; External API.
; --------------------------------

(defn get-cache-metadata-snapshot []
  (request-cache-process-sync
    {
      "action" "get_cache_metadata"
      "args" {}
    }))

(defn forward-resource-to-cache [resource data]
  (request-cache-process-async
    {
      "action" "forward_resource_to_cache"
      "args" {
        "resource" (filter-data-from-resource-object resource)
        "data" data
      }
    }))

(defn get-resource-from-cache [resource]
  (request-cache-process-sync
    {
      "action" "get_resource_from_cache"
      "args" {
        "resource" resource
      }
    }))

(defn are-resources-in-cache [resources]
  (request-cache-process-sync
    {
      "action" "are_resources_in_cache"
      "args" {
        "resources" resources
      }
    }))

(defn reset-cache []
  (request-cache-process-sync
    {
      "action" "reset_cache"
      "args" {}
    }))

; --------------------------------
; Implementation.
; --------------------------------

(defn do-reset-cache []
  (setv action {
    "name" "reset_cache"
  })
  (apply-cache-action action)
  (persist-cache-metadata (update-cache-metadata-for-action {} action)))

(defn do-forward-resource-to-cache [resource data]
    (setv cache-metadata (get-cache-metadata))
    ; TODO Maintain metrics on resource usage, for eg:
    ; - resources inputs for last 24 hours;
    ; - last N (10000) resources inputs.
    ; With this data + hit logs, we could process cache efficiency metrics.
    ; TODO Logs this data and create datasets, so we can try strategies and
    ; see which ones work best on past-data.
    (setv actions
        ; - Decide what to do with current resource -> actions;
        (process-resource-caching-decision cache-metadata resource data))
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
        (when ENABLE-SANITY-CHECKS
          (apply-sanity-check))
    )

(defn do-get-resource-from-cache [resource]
  ; TODO Cache usage.
  ; Maintain statistics on cache hits,
  ; with volumes of input resource bandwitdh hit/missed.
  (setv cache-metadata (get-cache-metadata))
  (setv resource-hash (get resource "body_source" "hash"))
  (if (is-resource-cached cache-metadata resource-hash)
    (get-cached-data resource-hash)
    None))

(defn do-are-resources-in-cache [resources]
  ; TODO Keep stats on resources asked, so we can use it
  ; in our cache decision making.
  (setv cache-metadata (get-cache-metadata))
  (list (map
    (fn [resource] (fun-merge-dicts [
      resource
      {
        "hit" (is-resource-cached cache-metadata (get resource "hash"))
      }
    ]))
    resources)))

; --------------------------------
; Decision making.
; --------------------------------

(defn is-resource-cached [cache-metadata resource-hash]
  (in resource-hash (get cache-metadata "cached_resources")))

(defn filter-data-from-resource-object [resource]
  (fun-merge-dicts [
    resource
    {
      "body_source" (fun-merge-dicts [
        (get resource "body_source")
        {
          "raw_base64" None
          "raw_string" None
        }
      ])
    }
  ]))

(defn map-add-resource-action [resource data]
  {
    "name" "add_resource"
    "resource" resource
    "data" data
  })

(defn map-remove-resource-action [resource]
  {
    "name" "remove_resource"
    "resource" resource
  })

(defn free-space-from-first-rec [resources size-to-free actions]
  (if (> size-to-free 0)
    (free-space-from-first-rec
      (list (drop 1 resources))
      (- size-to-free (get (first resources) "size"))
      (+ actions [(map-remove-resource-action (first resources))]))
    actions))

(defn free-space-from-old-entries [cache-metadata size-to-free]
  (setv ordered-resources (fun-sort (.values (get cache-metadata "cached_resources")) (fn [resource] (get resource "added_at"))))
  ; (logger.debug "Ordered resources: %s" ordered-resources)
  (if (> size-to-free 0)
    ; Order resources by timestamp.
    ; Remove until we have freed the specified size
    (free-space-from-first-rec
      ordered-resources
      size-to-free
      [])
    []))

(defn process-resource-caching-decision [cache-metadata resource data]
    ; Naive FIFO cache:
    ; TODO Uses resources stats to cache the most used resources.
    (if (and
      ; - Check for a caching size threshold;
      (>= (get resource "data_spec" "size") MIN-FILE-SIZE-CACHE-THRESHOLD)
      ; - Check that not more than half the max cache size;
      (< (get resource "data_spec" "size") (/ MAX-RESOURCES-CACHE-SIZE 2))
      ; - Check if already cached;
      (not (is-resource-cached cache-metadata (get resource "data_spec" "hash")))
    )
      (+
        ; - (If threshold passed) add to cache;
        [
          (map-add-resource-action resource data)
        ]
        ; - Remove from cache if max cache size reached (remove older cache entries).
        (free-space-from-old-entries
          cache-metadata
          (- 
            ; New size with added resource - max allowed size = size to free.
            (+ (get cache-metadata "total_size") (get resource "data_spec" "size"))
            MAX-RESOURCES-CACHE-SIZE
          ))
      )
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
        "free_remaining_size" MAX-RESOURCES-CACHE-SIZE
        "cached_resources" {}
        "hashing_algorighm" "sha256"
    })

(defn process-cache-total-size [resources]
  (sum (map
    (fn [resource] (get resource "size"))
    resources)))

(defn update-cache-metadata-metrics [cache-metadata]
  (setv total-size (process-cache-total-size (.values (get cache-metadata "cached_resources"))))
  (fun-merge-dicts [
    cache-metadata
    {
      "total_size" total-size
      "free_remaining_size" (- MAX-RESOURCES-CACHE-SIZE total-size)
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
        "cached_resources" (fun-dict-remove-key (get cache-metadata "cached_resources") (get resource "hash"))
      }
    ])))

(defn update-cache-metadata-for-action [cache-metadata action]
  (setv action-name (get action "name"))
  (cond
    (= action-name "reset_cache")
    (init-cache-metadata)

    (= action-name "add_resource")
    (add-resource-to-cache-metadata cache-metadata (get action "resource"))

    (= action-name "remove_resource")
    (remove-resource-from-cache-metadata cache-metadata (get action "resource"))

    True
    (raise (RuntimeError (.format "Unsupported cache action '{}'" action-name)))
  ))
