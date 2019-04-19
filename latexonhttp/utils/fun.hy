(defn fun-merge-dicts [dicts]
    (setv merged-dict {})
    (for [one-dict dicts]
        ((fn [one-dict]
            (.update merged-dict one-dict))
            one-dict))
    merged-dict)

(defn fun-sort [collections sort-fn]
    (sorted collections :key sort-fn))


(defn get-default [value key default]
  (if (in key value)
    (get value key)
    default))
