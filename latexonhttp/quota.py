"""
latexonhttp.quota
~~~~~~~~~~~~~~~~~
Fair-use quota and rate limiting for compilation endpoints.

Hot quota state (per-IP window counters, violations, bans) is kept in a
Valkey store so that the request path never queries PostgreSQL. The quota is
active only when VALKEY_HOST is configured; when the store is unreachable it
fails open (requests are allowed, the failure is logged and reported).

:copyright: (c) 2026 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

import logging
import os
import threading
import time
from datetime import UTC, datetime

import envparse

try:
    import valkey
except ImportError:  # The quota fails open without its store client.
    valkey = None

import sentry_sdk

logger = logging.getLogger(__name__)

# Configuration (read once at import, like the other application modules).

VALKEY_HOST = os.getenv("VALKEY_HOST")
VALKEY_PORT = int(os.getenv("VALKEY_PORT", "6379"))
VALKEY_DB = int(os.getenv("VALKEY_DB", "0"))
# Bounded wait on the store: a dead Valkey must not stall every request.
STORE_TIMEOUT = float(os.getenv("QUOTA_STORE_TIMEOUT", "1"))

QUOTA_ENABLED = envparse.env("QUOTA_ENABLED", cast=bool, default=True)
# "open": allow requests when the store is unavailable; "closed": reject them.
QUOTA_FAIL_MODE = envparse.env("QUOTA_FAIL_MODE", cast=str, default="open")
QUOTA_CLIENT_IP_HEADER = envparse.env(
    "QUOTA_CLIENT_IP_HEADER", cast=str, default="X-Forwarded-For"
)


def _parse_trusted_ips(raw):
    return {entry.strip() for entry in (raw or "").split(",") if entry.strip()}


# Clients bypassing the quota entirely (monitoring probes, tests).
QUOTA_TRUSTED_IPS = _parse_trusted_ips(os.getenv("QUOTA_TRUSTED_IPS"))

QUOTA_LIMITS = {
    "second": envparse.env("QUOTA_LIMIT_SECOND", cast=int, default=2),
    "minute": envparse.env("QUOTA_LIMIT_MINUTE", cast=int, default=6),
    "hour": envparse.env("QUOTA_LIMIT_HOUR", cast=int, default=40),
    "day": envparse.env("QUOTA_LIMIT_DAY", cast=int, default=150),
    "week": envparse.env("QUOTA_LIMIT_WEEK", cast=int, default=400),
}
PERIODS = ("second", "minute", "hour", "day", "week")
WINDOW_LENGTHS = {"second": 1, "minute": 60, "hour": 3600}
# Counter TTL: window length + slack so a window key cannot be recycled.
COUNTER_TTLS = {
    "second": 3,
    "minute": 75,
    "hour": 3720,
    "day": 90000,
    "week": 691200,
}

# Escalation: clients that keep firing while over quota get banned.
QUOTA_BAN_SHORT_VIOLATIONS = envparse.env(
    "QUOTA_BAN_SHORT_VIOLATIONS", cast=int, default=3
)
QUOTA_BAN_SHORT_DURATION = envparse.env(
    "QUOTA_BAN_SHORT_DURATION", cast=int, default=3600
)
QUOTA_BAN_LONG_VIOLATIONS = envparse.env(
    "QUOTA_BAN_LONG_VIOLATIONS", cast=int, default=10
)
QUOTA_BAN_COUNT_FOR_LONG = envparse.env("QUOTA_BAN_COUNT_FOR_LONG", cast=int, default=3)
QUOTA_BAN_LONG_DURATION = envparse.env(
    "QUOTA_BAN_LONG_DURATION", cast=int, default=86400
)
QUOTA_VIOLATION_SHORT_WINDOW = envparse.env(
    "QUOTA_VIOLATION_SHORT_WINDOW", cast=int, default=900
)
QUOTA_VIOLATION_LONG_WINDOW = envparse.env(
    "QUOTA_VIOLATION_LONG_WINDOW", cast=int, default=86400
)

_client = None
_client_lock = threading.Lock()


def _get_client():
    """Lazily build the Valkey client; None when no host is configured."""
    global _client
    if not VALKEY_HOST or valkey is None:
        return None
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = valkey.Valkey(
                    host=VALKEY_HOST,
                    port=VALKEY_PORT,
                    db=VALKEY_DB,
                    decode_responses=True,
                    socket_connect_timeout=STORE_TIMEOUT,
                    socket_timeout=STORE_TIMEOUT,
                )
    return _client


def get_client_ip(request):
    """Resolve the client IP from the trusted header, then the socket peer.

    The reverse proxy forwards the real client IP in X-Forwarded-For
    (single-hop deployment; request.remote_addr is the proxy itself).
    """
    forwarded = request.headers.get(QUOTA_CLIENT_IP_HEADER)
    if forwarded:
        # First value of the list; the deployment proxies a single hop.
        first_hop = forwarded.split(",")[0].strip()
        if first_hop:
            return first_hop
    return request.remote_addr or "unknown"


def window_bucket(period, epoch):
    """Return (bucket_key, window_end_epoch) for a calendar-aligned window."""
    if period in WINDOW_LENGTHS:
        length = WINDOW_LENGTHS[period]
        bucket = epoch // length
        return str(bucket), (bucket + 1) * length
    moment = datetime.fromtimestamp(epoch, tz=UTC)
    if period == "day":
        midnight = moment.replace(hour=0, minute=0, second=0, microsecond=0)
        return moment.strftime("%Y%m%d"), int(midnight.timestamp()) + 86400
    if period == "week":
        iso = moment.isocalendar()
        monday = datetime.fromisocalendar(iso.year, iso.week, 1).replace(tzinfo=UTC)
        return f"{iso.year}-W{iso.week:02d}", int(monday.timestamp()) + 604800
    raise ValueError(f"Unknown quota period: {period}")


def _ban_key(client_ip):
    return f"quota:ban:{client_ip}"


def _counter_key(client_ip, period, bucket_key):
    return f"quota:c:{client_ip}:{period}:{bucket_key}"


def _ban_duration(level):
    return QUOTA_BAN_LONG_DURATION if level == "long" else QUOTA_BAN_SHORT_DURATION


def _get_str(client, key):
    value = client.get(key)
    return None if value is None else str(value)


def _increment_with_expiry(client, key, ttl):
    """INCR a counter and arm its TTL on first creation (race-safe)."""
    value = int(client.incr(key))
    if value == 1:
        client.expire(key, ttl, nx=True)
    return value


def _count_request(client, client_ip, epoch):
    """Record one admitted request in the five windows (one round-trip)."""
    pipe = client.pipeline(transaction=True)
    for period in PERIODS:
        bucket_key, _ = window_bucket(period, epoch)
        key = _counter_key(client_ip, period, bucket_key)
        pipe.incr(key)
        # EXPIRE NX: arm the TTL when the key is new, keep it otherwise.
        pipe.expire(key, COUNTER_TTLS[period], nx=True)
    results = pipe.execute()
    counts = {period: int(results[index * 2]) for index, period in enumerate(PERIODS)}
    return counts


def _rollback_counts(client, client_ip, epoch):
    """Denied requests must not consume quota: undo the counter increments."""
    pipe = client.pipeline(transaction=True)
    for period in PERIODS:
        bucket_key, _ = window_bucket(period, epoch)
        key = _counter_key(client_ip, period, bucket_key)
        pipe.decr(key)
        # NX: keep the armed TTL; only re-arm it if DECR recreated a key
        # whose window already rolled over (a stray self-expiring negative).
        pipe.expire(key, COUNTER_TTLS[period], nx=True)
    pipe.execute()


def _register_violation(client, client_ip):
    """Count one quota violation and return the escalation counters."""
    short_key = f"quota:viol:15m:{client_ip}"
    long_key = f"quota:viol:24h:{client_ip}"
    bans_key = f"quota:bans:24h:{client_ip}"
    _increment_with_expiry(client, short_key, QUOTA_VIOLATION_SHORT_WINDOW)
    _increment_with_expiry(client, long_key, QUOTA_VIOLATION_LONG_WINDOW)
    pipe = client.pipeline(transaction=True)
    pipe.get(short_key)
    pipe.get(long_key)
    pipe.get(bans_key)
    short_violations, long_violations, bans = pipe.execute()
    return {
        "short": int(short_violations or 0),
        "long": int(long_violations or 0),
        "bans": int(bans or 0),
    }


def _escalation_level(violations, current_ban=None):
    """Decide the ban level from the violation counters.

    Long-ban conditions win over the short-ban threshold; a client already
    banned keeps its level unless it escalates.
    """
    if (
        violations["long"] >= QUOTA_BAN_LONG_VIOLATIONS
        or violations["bans"] >= QUOTA_BAN_COUNT_FOR_LONG
    ):
        return "long"
    if current_ban == "long":
        return "long"
    if violations["short"] >= QUOTA_BAN_SHORT_VIOLATIONS:
        return "short"
    return current_ban


def _apply_ban(client, client_ip, level, count_episode, rearm=False):
    """Arm (or re-arm) a ban; count a new ban episode when requested."""
    if count_episode:
        bans = _increment_with_expiry(
            client, f"quota:bans:24h:{client_ip}", QUOTA_VIOLATION_LONG_WINDOW
        )
        if bans >= QUOTA_BAN_COUNT_FOR_LONG:
            level = "long"
    client.set(_ban_key(client_ip), level, ex=_ban_duration(level))
    log = logger.debug if rearm else logger.warning
    log(
        "Quota ban (%s) applied to %s for %s seconds",
        level,
        client_ip,
        _ban_duration(level),
    )
    return level


def _decision(
    *,
    allowed,
    period=None,
    limit=None,
    remaining=None,
    reset=None,
    retry_after=None,
    banned=False,
    ban_expires_at=None,
    unavailable=False,
):
    return {
        "allowed": allowed,
        "period": period,
        "limit": limit,
        "remaining": remaining,
        "reset": reset,
        "retry_after": retry_after,
        "banned": banned,
        "ban_expires_at": ban_expires_at,
        "unavailable": unavailable,
    }


def _deny_for_ban(client, client_ip, epoch):
    ttl = int(client.ttl(_ban_key(client_ip)))
    if ttl < 1:
        # The ban expired between the check and here; do not deny on a stale
        # read, the request proceeds uncounted this once.
        return None
    return _decision(
        allowed=False,
        period=None,
        limit=None,
        remaining=0,
        reset=epoch + ttl,
        retry_after=ttl,
        banned=True,
        ban_expires_at=epoch + ttl,
    )


def _check_with_store(client, client_ip, epoch):
    ban_level = _get_str(client, _ban_key(client_ip))
    if ban_level is not None:
        # Hammering during a ban re-arms it and feeds the escalation counters.
        violations = _register_violation(client, client_ip)
        level = _escalation_level(violations, current_ban=ban_level)
        _apply_ban(
            client, client_ip, level, count_episode=False, rearm=level == ban_level
        )
        denial = _deny_for_ban(client, client_ip, epoch)
        if denial is None:
            return None  # Ban just expired; let the request through uncounted.
        logger.info(
            "Quota denial (ban) for %s; level %s, retry after %s s",
            client_ip,
            ban_level,
            denial["retry_after"],
        )
        return denial

    counts = _count_request(client, client_ip, epoch)
    breached = next(
        (period for period in PERIODS if counts[period] > QUOTA_LIMITS[period]),
        None,
    )
    if breached:
        _rollback_counts(client, client_ip, epoch)
        limit = QUOTA_LIMITS[breached]
        window_end = window_bucket(breached, epoch)[1]
        violations = _register_violation(client, client_ip)
        level = _escalation_level(violations)
        ban_expires_at = None
        retry_after = max(window_end - epoch, 1)
        if level:
            level = _apply_ban(client, client_ip, level, count_episode=True)
            ban_expires_at = epoch + _ban_duration(level)
            retry_after = _ban_duration(level)
        logger.info(
            "Quota denial for %s; %s window exceeded (%s/%s)",
            client_ip,
            breached,
            counts[breached],
            limit,
        )
        return _decision(
            allowed=False,
            period=breached,
            limit=limit,
            remaining=0,
            reset=window_end,
            retry_after=retry_after,
            banned=level is not None,
            ban_expires_at=ban_expires_at,
        )

    # Allowed: report the most-constrained window in the rate-limit headers.
    binding = min(PERIODS, key=lambda period: QUOTA_LIMITS[period] - counts[period])
    limit = QUOTA_LIMITS[binding]
    return _decision(
        allowed=True,
        period=binding,
        limit=limit,
        remaining=limit - counts[binding],
        reset=window_bucket(binding, epoch)[1],
    )


def check_quota(client_ip, now=None):
    """Check and record one request for a client IP.

    Returns a decision dict, or None when the quota does not apply
    (disabled, allowlisted client, or store unavailable with fail-open).
    """
    if not QUOTA_ENABLED:
        return None
    if client_ip in QUOTA_TRUSTED_IPS:
        return None
    client = _get_client()
    if client is None:
        return None
    epoch = int(time.time()) if now is None else int(now)
    try:
        return _check_with_store(client, client_ip, epoch)
    except Exception:
        logger.exception("Quota store unreachable; failing %s", QUOTA_FAIL_MODE)
        sentry_sdk.capture_exception()
        if QUOTA_FAIL_MODE == "closed":
            return _decision(allowed=False, unavailable=True)
        return None


def rate_limit_headers(decision):
    """Rate-limit headers for a decision (denials and allowances alike)."""
    headers = {}
    if decision.get("retry_after") is not None:
        headers["Retry-After"] = str(int(decision["retry_after"]))
    if decision.get("limit") is not None:
        headers["X-RateLimit-Limit"] = str(decision["limit"])
        headers["X-RateLimit-Remaining"] = str(max(int(decision["remaining"]), 0))
    if decision.get("reset") is not None:
        headers["X-RateLimit-Reset"] = str(int(decision["reset"]))
    return headers


def quota_rejection(decision):
    """Build the (body, status, headers) tuple for a denied request."""
    if decision.get("unavailable"):
        return ({"error": "QUOTA_STORE_UNAVAILABLE"}, 503, {})
    body = {
        "error": "QUOTA_EXCEEDED",
        "message": "Fair-use quota exceeded. Slow down, or wait for the window to reset.",
        "quota": {
            "period": decision.get("period"),
            "limit": decision.get("limit"),
            "retry_after": decision.get("retry_after"),
            "banned": bool(decision.get("banned")),
            "ban_expires_at": decision.get("ban_expires_at"),
        },
    }
    return (body, 429, rate_limit_headers(decision))
