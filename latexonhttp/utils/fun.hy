#! /usr/bin/env hy
"""
    latexonhttp.utils.fun
    ~~~~~~~~~~~~~~~~~~~~~
    LaTeX-On-HTTP functional programming utilities.

    :copyright: (c) 2019-2022 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
(import
    functools [reduce])

(defn fun-merge-dicts [dicts]
    (setv merged-dict {})
    (for [one-dict dicts]
        ((fn [one-dict]
            (.update merged-dict one-dict))
            one-dict))
    merged-dict)


(defn fun-sort [collection sort-fn]
    (sorted collection :key sort-fn))


(defn fun-dict-update [original-dict update-dict]
  (.update original-dict update-dict)
  original-dict)


(defn fun-dict-remove-key [original-dict key]
  (.pop original-dict key)
  original-dict)


(defn fun-count-pred [collection pred-fn]
    ; As map returns an iterable, this don't iterate twice (from my understanding).
    ; https://docs.python.org/3/library/itertools.html
    (sum
        (map
            (fn [value] (if (pred-fn value) 1 0))
            collection)))


(defn all-pred [collection pred-fn]
    (all (map pred-fn collection)))


(defn any-pred [collection pred-fn]
    (any (map pred-fn collection)))


(defn get-default [value key [default None]]
  (if (in key value)
    (get value key)
    default))
