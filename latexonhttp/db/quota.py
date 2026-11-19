"""PostgreSQL persistence for quota ban decisions."""

from datetime import UTC, datetime
from uuid import uuid4

from latexonhttp.db.jobs import _get_pool

_COLUMNS = (
    "id",
    "client_ip",
    "level",
    "source",
    "trigger_period",
    "violations_short",
    "violations_long",
    "bans_24h",
    "armed_at",
    "expires_at",
)
_LEVELS = frozenset({"short", "long"})
_SOURCES = frozenset({"violation_window", "ban_escalation"})
_PERIODS = frozenset({"second", "minute", "hour", "day", "week"})


def record_ban(event):
    """Insert one durable ban record from a quota enforcement event.

    The event carries the client IP, the ban level, its source, the
    escalation counters snapshot, and the arming epoch plus the ban
    duration; this module owns the row id and the timestamp conversion.
    """
    level = event["level"]
    source = event["source"]
    trigger_period = event.get("trigger_period")
    if level not in _LEVELS:
        raise ValueError(f"Unsupported ban level: {level!r}")
    if source not in _SOURCES:
        raise ValueError(f"Unsupported ban source: {source!r}")
    if trigger_period is not None and trigger_period not in _PERIODS:
        raise ValueError(f"Unsupported ban trigger period: {trigger_period!r}")
    violations = event["violations"]
    row = {
        "id": str(uuid4()),
        "client_ip": event["client_ip"],
        "level": level,
        "source": source,
        "trigger_period": trigger_period,
        "violations_short": violations.get("short"),
        "violations_long": violations.get("long"),
        "bans_24h": violations.get("bans"),
        "armed_at": datetime.fromtimestamp(event["epoch"], UTC),
        "expires_at": datetime.fromtimestamp(event["epoch"] + event["duration"], UTC),
    }
    with _get_pool().connection() as connection, connection.cursor() as cursor:
        columns = ", ".join(_COLUMNS)
        placeholders = ", ".join(["%s"] * len(_COLUMNS))
        cursor.execute(
            f"INSERT INTO quota_bans ({columns}) VALUES ({placeholders})",
            [row[column] for column in _COLUMNS],
        )
