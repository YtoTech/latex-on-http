#! /usr/bin/env hy
"""
    latexonhttp.usage
    ~~~~~~~~~~~~~~~~~
    API usage token scoring.

    Every compilation request is scored over four categories -- incoming
    data, resource fetching (discounted by the input cache), processing
    time and outgoing data -- summed into a single number, the usage
    tokens of the request. The score is measured and persisted with the
    job metadata; applying limits stays with the quota.

    1 token = 1 KiB of data or 1 second of server occupancy, before
    weighting. Raw measures are persisted too, so weights stay tunable
    from production data without rewriting history.

    :copyright: (c) 2026 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
(import envparse [env])

; --------------------------------------------
; Configuration (read once at import, like the other application modules).
; --------------------------------------------

; Score unit: 1 token = 1 KiB of data or 1 second of server occupancy.
(setv DATA-UNIT 1024)

(setv USAGE-WEIGHTS {
    "incoming" (env "USAGE_WEIGHT_INCOMING" :cast float :default 1.0)
    "fetch" (env "USAGE_WEIGHT_FETCH" :cast float :default 1.0)
    ; Cache-hit bytes are free by default: only network-fetched bytes count.
    "cache" (env "USAGE_WEIGHT_CACHE" :cast float :default 0.0)
    "processing" (env "USAGE_WEIGHT_PROCESSING" :cast float :default 1.0)
    "outgoing" (env "USAGE_WEIGHT_OUTGOING" :cast float :default 1.0)})

; --------------------------------------------
; Usage record (opened at admission by the API module).
; --------------------------------------------

(defn new-usage [received-at payload-size]
    """
    Open the usage record of a request: when it was received
    (for the processing time) and how many bytes came in.
    """
    {"received_at" received-at
     "incoming_bytes" payload-size})

(defn processing-seconds [usage replied-at]
    """
    Wall-clock server occupancy of the request, received to replied.
    """
    (max (.total_seconds (- replied-at (get usage "received_at"))) 0.0))

(defn fetched-effective-bytes [fetched]
    """
    Bytes charged for resource fetching: the ones actually fetched,
    with cache-hit bytes discounted by their weight.

    `fetched` carries the fetching metadata of the job
    (fetched_resources_size, fetched_resources_cache_hits_size).
    """
    (setv fetched-size (get fetched "fetched_resources_size"))
    (setv cache-hits-size (get fetched "fetched_resources_cache_hits_size"))
    (+ (- fetched-size cache-hits-size)
       (* (get USAGE-WEIGHTS "cache") cache-hits-size)))

(defn _data-tokens [bytes-count]
    (/ bytes-count DATA-UNIT))

(defn usage-scores [usage fetched replied-at outgoing-size]
    """
    Compute the usage score of one request, at reply time.

    Returns the tokens per category (incoming, fetch, processing,
    outgoing) and their total, rounded to 6 decimals so the
    components always add up to the stored total.
    """
    (setv components {
        "incoming" (* (get USAGE-WEIGHTS "incoming")
                      (_data-tokens (get usage "incoming_bytes")))
        "fetch" (* (get USAGE-WEIGHTS "fetch")
                   (_data-tokens (fetched-effective-bytes fetched)))
        "processing" (* (get USAGE-WEIGHTS "processing")
                        (processing-seconds usage replied-at))
        "outgoing" (* (get USAGE-WEIGHTS "outgoing")
                      (_data-tokens outgoing-size))})
    (setv scores (dict (lfor
        [category tokens] (.items components)
        [category (round tokens 6)])))
    (setv (get scores "total") (round (sum (.values scores)) 6))
    scores)
