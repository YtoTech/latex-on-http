#! /usr/bin/env hy
"""
    latexonhttp.quota
    ~~~~~~~~~~~~~~~~~
    Fair-use quota and rate limiting for compilation endpoints.

    Hot quota state (per-IP window counters, violations, bans) is kept in a
    Valkey store so that the request path never queries PostgreSQL. The quota
    is active only when VALKEY_HOST is configured; when the store is
    unreachable it fails open (requests are allowed, the failure is logged
    and reported).

    :copyright: (c) 2026 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
(import logging os threading time)
(import datetime [UTC datetime])
(import envparse [env])
(import sentry_sdk)

(try
    (import valkey)
    (except [ImportError]
        ; The quota fails open without its store client.
        (setv valkey None)))

(setv logger (.getLogger logging __name__))

; --------------------------------------------
; Configuration (read once at import, like the other application modules).
; --------------------------------------------

(setv VALKEY-HOST (os.getenv "VALKEY_HOST"))
(setv VALKEY-PORT (int (os.getenv "VALKEY_PORT" "6379")))
(setv VALKEY-DB (int (os.getenv "VALKEY_DB" "0")))
; Bounded wait on the store: a dead Valkey must not stall every request.
(setv STORE-TIMEOUT (float (os.getenv "QUOTA_STORE_TIMEOUT" "1")))

(setv QUOTA-ENABLED (env "QUOTA_ENABLED" :cast bool :default True))
; "open": allow requests when the store is unavailable; "closed": reject them.
(setv QUOTA-FAIL-MODE (env "QUOTA_FAIL_MODE" :cast str :default "open"))
(setv QUOTA-CLIENT-IP-HEADER (env "QUOTA_CLIENT_IP_HEADER" :cast str :default "X-Forwarded-For"))

(defn parse-trusted-ips [raw]
    (setv entries (lfor
        entry (.split (or raw "") ",")
        :setv stripped (.strip entry)
        :if stripped
        stripped))
    (set entries))

; Clients bypassing the quota entirely (monitoring probes, tests).
(setv QUOTA-TRUSTED-IPS (parse-trusted-ips (os.getenv "QUOTA_TRUSTED_IPS")))

(setv QUOTA-LIMITS {
    "second" (env "QUOTA_LIMIT_SECOND" :cast int :default 2)
    "minute" (env "QUOTA_LIMIT_MINUTE" :cast int :default 6)
    "hour" (env "QUOTA_LIMIT_HOUR" :cast int :default 40)
    "day" (env "QUOTA_LIMIT_DAY" :cast int :default 150)
    "week" (env "QUOTA_LIMIT_WEEK" :cast int :default 400)})
(setv PERIODS ["second" "minute" "hour" "day" "week"])
(setv WINDOW-LENGTHS {"second" 1 "minute" 60 "hour" 3600})
; Counter TTL: window length + slack so a window key cannot be recycled.
(setv COUNTER-TTLS {
    "second" 3
    "minute" 75
    "hour" 3720
    "day" 90000
    "week" 691200})

; Escalation: clients that keep firing while over quota get banned.
(setv QUOTA-BAN-SHORT-VIOLATIONS (env "QUOTA_BAN_SHORT_VIOLATIONS" :cast int :default 3))
(setv QUOTA-BAN-SHORT-DURATION (env "QUOTA_BAN_SHORT_DURATION" :cast int :default 3600))
(setv QUOTA-BAN-LONG-VIOLATIONS (env "QUOTA_BAN_LONG_VIOLATIONS" :cast int :default 10))
(setv QUOTA-BAN-COUNT-FOR-LONG (env "QUOTA_BAN_COUNT_FOR_LONG" :cast int :default 3))
(setv QUOTA-BAN-LONG-DURATION (env "QUOTA_BAN_LONG_DURATION" :cast int :default 86400))
(setv QUOTA-VIOLATION-SHORT-WINDOW (env "QUOTA_VIOLATION_SHORT_WINDOW" :cast int :default 900))
(setv QUOTA-VIOLATION-LONG-WINDOW (env "QUOTA_VIOLATION_LONG_WINDOW" :cast int :default 86400))

; --------------------------------------------
; Valkey client (lazy singleton, like the PostgreSQL pool).
; --------------------------------------------

(setv _client None)
(setv _client-lock (threading.Lock))

(defn _get-client []
    """
    Lazily build the Valkey client; None when no host is configured.
    """
    (global _client)
    (cond
        (or (not VALKEY-HOST) (is valkey None)) None
        (not (is _client None)) _client
        True (do
            (when (is _client None)
                (setv _client (valkey.Valkey
                    :host VALKEY-HOST
                    :port VALKEY-PORT
                    :db VALKEY-DB
                    :decode-responses True
                    :socket-connect-timeout STORE-TIMEOUT
                    :socket-timeout STORE-TIMEOUT)))
            _client)))

; --------------------------------------------
; Client IP extraction.
; --------------------------------------------

(defn get-client-ip [request]
    """
    Resolve the client IP from the trusted header, then the socket peer.

    The reverse proxy forwards the real client IP in X-Forwarded-For
    (single-hop deployment; request.remote_addr is the proxy itself).
    """
    (setv forwarded (.get request.headers QUOTA-CLIENT-IP-HEADER None))
    (setv first-hop (.strip (get (.split (or forwarded "") ",") 0)))
    (or first-hop (or request.remote_addr "unknown")))

; --------------------------------------------
; Windows and keys (calendar-aligned fixed windows, UTC).
; --------------------------------------------

(defn window-bucket [period epoch]
    """
    Return [bucket-key, window-end-epoch] for a calendar-aligned window.
    """
    (setv length (.get WINDOW-LENGTHS period None))
    (if length
        (do
            (setv bucket (// epoch length))
            [(str bucket) (* (+ bucket 1) length)])
        (cond
            (= period "day")
                (do
                    (setv moment (datetime.fromtimestamp epoch UTC))
                    (setv midnight (.replace moment :hour 0 :minute 0 :second 0 :microsecond 0))
                    [(.strftime moment "%Y%m%d")
                     (+ (int (.timestamp midnight)) 86400)])
            (= period "week")
                (do
                    (setv [iso-year iso-week _day]
                        (.isocalendar (datetime.fromtimestamp epoch UTC)))
                    (setv monday (.replace
                        (datetime.fromisocalendar iso-year iso-week 1)
                        :tzinfo UTC))
                    [(.format "{}-W{:02d}" iso-year iso-week)
                     (+ (int (.timestamp monday)) 604800)])
            True (raise (ValueError (.format "Unknown quota period: {}" period))))))

(defn _counter-key [client-ip period bucket-key]
    (.format "quota:c:{}:{}:{}" client-ip period bucket-key))

(defn ban-key [client-ip]
    (.format "quota:ban:{}" client-ip))

(defn ban-duration [level]
    (if (= level "long") QUOTA-BAN-LONG-DURATION QUOTA-BAN-SHORT-DURATION))

; --------------------------------------------
; Store operations.
; --------------------------------------------

(defn get-str [client key]
    (let [value (client.get key)]
        (if (is value None) None (str value))))

(defn increment-with-expiry [client key ttl]
    """
    INCR a counter and arm its TTL on first creation (race-safe).
    """
    (setv value (int (client.incr key)))
    (when (= value 1)
        ; EXPIRE NX: arm the TTL when the key is new, keep it otherwise.
        (client.expire key ttl :nx True))
    value)

(defn count-request [client client-ip epoch]
    """
    Record one admitted request in the five windows (one round-trip).
    """
    (setv pipe (client.pipeline :transaction True))
    (for [period PERIODS]
        (setv key (_counter-key client-ip period (get (window-bucket period epoch) 0)))
        (.incr pipe key)
        (.expire pipe key (get COUNTER-TTLS period) :nx True))
    (dict (zip PERIODS (cut (.execute pipe) None None 2))))

(defn _rollback-counts [client client-ip epoch]
    """
    Denied requests must not consume quota: undo the counter increments.
    """
    (setv pipe (client.pipeline :transaction True))
    (for [period PERIODS]
        (setv key (_counter-key client-ip period (get (window-bucket period epoch) 0)))
        (.decr pipe key)
        ; NX: keep the armed TTL; only re-arm it if DECR recreated a key
        ; whose window already rolled over (a stray self-expiring negative).
        (.expire pipe key (get COUNTER-TTLS period) :nx True))
    (.execute pipe)
    None)

(defn register-violation [client client-ip]
    """
    Count one quota violation and return the escalation counters.
    """
    (increment-with-expiry
        client (.format "quota:viol:15m:{}" client-ip) QUOTA-VIOLATION-SHORT-WINDOW)
    (increment-with-expiry
        client (.format "quota:viol:24h:{}" client-ip) QUOTA-VIOLATION-LONG-WINDOW)
    (setv pipe (client.pipeline :transaction True))
    (.get pipe (.format "quota:viol:15m:{}" client-ip))
    (.get pipe (.format "quota:viol:24h:{}" client-ip))
    (.get pipe (.format "quota:bans:24h:{}" client-ip))
    (setv [short-violations long-violations bans] (.execute pipe))
    {
        "short" (int (or short-violations 0))
        "long" (int (or long-violations 0))
        "bans" (int (or bans 0))})

; --------------------------------------------
; Escalation.
; --------------------------------------------

(defn escalation-level [violations [current-ban None]]
    """
    Decide the ban level from the violation counters.

    Long-ban conditions win over the short-ban threshold; a client already
    banned keeps its level unless it escalates.
    """
    (cond
        (or (>= (get violations "long") QUOTA-BAN-LONG-VIOLATIONS)
            (>= (get violations "bans") QUOTA-BAN-COUNT-FOR-LONG))
            "long"
        (= current-ban "long") "long"
        (>= (get violations "short") QUOTA-BAN-SHORT-VIOLATIONS) "short"
        True current-ban))

(defn apply-ban [client client-ip level count-episode [rearm False]]
    """
    Arm (or re-arm) a ban; count a new ban episode when requested.
    """
    (when count-episode
        (setv bans (increment-with-expiry
            client (.format "quota:bans:24h:{}" client-ip) QUOTA-VIOLATION-LONG-WINDOW))
        (when (>= bans QUOTA-BAN-COUNT-FOR-LONG)
            (setv level "long")))
    (client.set (ban-key client-ip) level :ex (ban-duration level))
    (if rearm
        (logger.info
            "Quota ban (%s) re-armed for %s (%s seconds)"
            level client-ip (ban-duration level))
        (logger.warning
            "Quota ban (%s) applied to %s for %s seconds"
            level client-ip (ban-duration level)))
    level)

; --------------------------------------------
; Decisions.
; --------------------------------------------

(defn _decision [allowed
                 [period None]
                 [limit None]
                 [remaining None]
                 [reset None]
                 [retry-after None]
                 [banned False]
                 [ban-expires-at None]
                 [unavailable False]]
    {"allowed" allowed
     "period" period
     "limit" limit
     "remaining" remaining
     "reset" reset
     "retry_after" retry-after
     "banned" banned
     "ban_expires_at" ban-expires-at
     "unavailable" unavailable})

(defn deny-for-ban [client client-ip epoch]
    (setv ttl (int (client.ttl (ban-key client-ip))))
    (if (< ttl 1)
        ; The ban expired between the check and here; do not deny on a
        ; stale read, the request proceeds uncounted this once.
        None
        (_decision
            :allowed False :remaining 0 :reset (+ epoch ttl) :retry-after ttl
            :banned True :ban-expires-at (+ epoch ttl))))

; --------------------------------------------
; Check flow.
; --------------------------------------------

(defn check-windows [client client-ip epoch]
    (setv counts (count-request client client-ip epoch))
    (setv breached (next
        (gfor
            period PERIODS
            :if (> (get counts period) (get QUOTA-LIMITS period))
            period)
        None))
    (if (is breached None)
        ; Allowed: report the most-constrained window in the headers.
        (do
            (setv binding (min
                PERIODS
                :key (fn [period] (- (get QUOTA-LIMITS period) (get counts period)))))
            (setv limit (get QUOTA-LIMITS binding))
            (_decision
                :allowed True :period binding :limit limit
                :remaining (- limit (get counts binding))
                :reset (get (window-bucket binding epoch) 1)))
        (do
            (_rollback-counts client client-ip epoch)
            (setv limit (get QUOTA-LIMITS breached))
            (setv window-end (get (window-bucket breached epoch) 1))
            (setv violations (register-violation client client-ip))
            (setv level (escalation-level violations))
            (setv retry-after (max (- window-end epoch) 1))
            (setv ban-expires-at None)
            (when level
                (setv level (apply-ban client client-ip level True))
                (setv ban-expires-at (+ epoch (ban-duration level)))
                (setv retry-after (ban-duration level)))
            (logger.info
                "Quota denial for %s; %s window exceeded (%s/%s)"
                client-ip breached (get counts breached) limit)
            (_decision
                :allowed False :period breached :limit limit :remaining 0
                :reset window-end :retry-after retry-after
                :banned (not (is level None))
                :ban-expires-at ban-expires-at))))

(defn check-with-store [client client-ip epoch]
    (setv ban-level (get-str client (ban-key client-ip)))
    (if (is ban-level None)
        (check-windows client client-ip epoch)
        (do
            ; Hammering during a ban re-arms it and feeds the escalation
            ; counters.
            (setv violations (register-violation client client-ip))
            (setv level (escalation-level violations :current-ban ban-level))
            (apply-ban client client-ip level False :rearm (= level ban-level))
            (setv denial (deny-for-ban client client-ip epoch))
            (if (is denial None)
                ; Ban just expired; let the request through uncounted.
                None
                (do
                    (logger.info
                        "Quota denial (ban) for %s; level %s, retry after %s s"
                        client-ip ban-level (get denial "retry_after"))
                    denial)))))

(defn check-quota [client-ip [now None]]
    """
    Check and record one request for a client IP.

    Returns a decision dict, or None when the quota does not apply
    (disabled, allowlisted client, or store unavailable with fail-open).
    """
    (if (or (not QUOTA-ENABLED) (in client-ip QUOTA-TRUSTED-IPS))
        None
        (let [client (_get-client)]
            (if (is client None)
                None
                (let [epoch (int (if (is now None) (time.time) now))]
                    (try
                        (check-with-store client client-ip epoch)
                        (except []
                            (logger.exception
                                "Quota store unreachable; failing %s" QUOTA-FAIL-MODE)
                            (sentry_sdk.capture_exception)
                            (if (= QUOTA-FAIL-MODE "closed")
                                (_decision :allowed False :unavailable True)
                                None))))))))

; --------------------------------------------
; HTTP contract helpers.
; --------------------------------------------

(defn rate-limit-headers [decision]
    """
    Rate-limit headers for a decision (denials and allowances alike).
    """
    (dict (lfor
        [header field] (zip
            ["Retry-After" "X-RateLimit-Limit" "X-RateLimit-Remaining" "X-RateLimit-Reset"]
            ["retry_after" "limit" "remaining" "reset"])
        :setv value (get decision field)
        :if (not (is value None))
        [header (str (int value))])))

(defn quota-rejection [decision [documentation-url None]]
    """
    Build the (body, status, headers) tuple for a denied request.

    When a documentation URL is provided, it is included in the body.
    The tuple (not a list!) matters: Flask only unpacks real tuples into
    the response triple.
    """
    (if (get decision "unavailable")
        (tuple [{"error" "QUOTA_STORE_UNAVAILABLE"} 503 {}])
        (do
            (setv body {
                "error" "QUOTA_EXCEEDED"
                "message" "Fair-use quota exceeded. Slow down, or wait for the window to reset."
                "quota" {"period" (get decision "period")
                         "limit" (get decision "limit")
                         "retry_after" (get decision "retry_after")
                         "banned" (bool (get decision "banned"))
                         "ban_expires_at" (get decision "ban_expires_at")}})
            (when documentation-url
                (setv (get body "documentation") documentation-url))
            (tuple [body 429 (rate-limit-headers decision)]))))
