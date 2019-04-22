(import [
    functools [reduce]
])

(defn fun-merge-dicts [dicts]
    (setv merged-dict {})
    (for [one-dict dicts]
        ((fn [one-dict]
            (.update merged-dict one-dict))
            one-dict))
    merged-dict)


(defn fun-sort [collection sort-fn]
    (sorted collection :key sort-fn))


(defn fun-count-pred [collection pred-fn]
    (reduce
        (fn [acc value] (if (pred-fn value) (+ acc 1) acc))
        collection
        0))


(defn get-default [value key default]
  (if (in key value)
    (get value key)
    default))
