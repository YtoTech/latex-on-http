"""PostgreSQL round-trip for the durable quota ban record."""

import os
from datetime import UTC, datetime

import psycopg
import pytest

from latexonhttp.db import jobs
from latexonhttp.db import quota as quota_db


@pytest.fixture
def postgres_database():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    jobs._pool = None
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute("TRUNCATE quota_bans")
    yield database_url
    if jobs._pool is not None:
        jobs._pool.close()
        jobs._pool = None
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute("TRUNCATE quota_bans")


def test_postgres_persists_a_ban_arming(postgres_database):
    quota_db.record_ban(
        {
            "client_ip": "203.0.113.7",
            "level": "short",
            "source": "violation_window",
            "trigger_period": "minute",
            "violations": {"short": 3, "long": 3, "bans": 1},
            "epoch": 1763559600,
            "duration": 3600,
        }
    )
    with psycopg.connect(postgres_database) as connection:
        row = connection.execute(
            "SELECT client_ip, level, source, trigger_period, violations_short,"
            " violations_long, bans_24h, armed_at, expires_at FROM quota_bans"
        ).fetchone()
    assert row == (
        "203.0.113.7",
        "short",
        "violation_window",
        "minute",
        3,
        3,
        1,
        datetime.fromtimestamp(1763559600, UTC),
        datetime.fromtimestamp(1763563200, UTC),
    )


def test_postgres_persists_a_ban_escalation(postgres_database):
    quota_db.record_ban(
        {
            "client_ip": "2001:db8::1",
            "level": "long",
            "source": "ban_escalation",
            "trigger_period": None,
            "violations": {"short": 10, "long": 10, "bans": 1},
            "epoch": 1763559600,
            "duration": 86400,
        }
    )
    with psycopg.connect(postgres_database) as connection:
        row = connection.execute(
            "SELECT client_ip, level, source, trigger_period FROM quota_bans"
        ).fetchone()
    assert row == ("2001:db8::1", "long", "ban_escalation", None)


def test_recorder_rejects_invalid_events():
    event = {
        "client_ip": "203.0.113.7",
        "level": "eternal",
        "source": "violation_window",
        "trigger_period": None,
        "violations": {},
        "epoch": 0,
        "duration": 1,
    }
    with pytest.raises(ValueError):
        quota_db.record_ban(event)
    event = dict(event, level="short", source="smoke")
    with pytest.raises(ValueError):
        quota_db.record_ban(event)
