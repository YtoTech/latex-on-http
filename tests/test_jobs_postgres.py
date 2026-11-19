import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import psycopg
import pytest

from latexonhttp.db import jobs


@pytest.fixture
def postgres_database():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    jobs._pool = None
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute("TRUNCATE jobs, user_agents RESTART IDENTITY")
    yield database_url
    if jobs._pool is not None:
        jobs._pool.close()
        jobs._pool = None
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute("TRUNCATE jobs, user_agents RESTART IDENTITY")


def metadata(user_agent=None):
    return {
        "id": str(uuid4()),
        "job_status": "received",
        "compiler": "pdflatex",
        "compilation_hash": None,
        "input_spec_mode": "json",
        "http_payload_size": 2**40,
        "cleaned_payload": {"resources": [{"content": True, "file": False}]},
        "remote_ip": "2001:db8::1",
        "forwarded_remote_ip": "203.0.113.1, 2001:db8::2",
        "user_agent": user_agent,
        "received_at": datetime.now(UTC),
    }


def test_postgres_accepts_null_user_agent_and_large_sizes(postgres_database):
    job = metadata()
    jobs.create_job(job)
    jobs.update_job(
        job["id"],
        job_status="completed",
        compilation_hash="a" * 64,
        fetched_resources_size=2**40,
        output_size=100_000_000,
    )

    with psycopg.connect(postgres_database) as connection:
        row = connection.execute(
            "SELECT user_agent_id, http_payload_size, fetched_resources_size, "
            "output_size, compilation_hash FROM jobs WHERE id = %s",
            (job["id"],),
        ).fetchone()
    assert row == (None, 2**40, 2**40, 100_000_000, "a" * 64)


def test_postgres_persists_usage_scores(postgres_database):
    job = metadata()
    jobs.create_job(job)
    jobs.update_job(
        job["id"],
        job_status="completed",
        response_size=123_456,
        usage_score_incoming=2.0,
        usage_score_fetch=1.5,
        usage_score_processing=3.25,
        usage_score_outgoing=120.5625,
        usage_score_total=127.3125,
    )

    with psycopg.connect(postgres_database) as connection:
        row = connection.execute(
            "SELECT response_size, usage_score_incoming, usage_score_fetch, "
            "usage_score_processing, usage_score_outgoing, usage_score_total "
            "FROM jobs WHERE id = %s",
            (job["id"],),
        ).fetchone()
    # NUMERIC(20,6) reads back as Decimal; exact fractions survive the round trip.
    assert row == (
        123_456,
        Decimal(2),
        Decimal(1.5),
        Decimal(3.25),
        Decimal(120.5625),
        Decimal(127.3125),
    )


def test_postgres_concurrent_jobs_share_one_user_agent(postgres_database):
    requests = [metadata("concurrent-agent") for _ in range(8)]
    with ThreadPoolExecutor(max_workers=len(requests)) as executor:
        list(executor.map(jobs.create_job, requests))

    with psycopg.connect(postgres_database) as connection:
        user_agent_count = connection.execute(
            "SELECT COUNT(*) FROM user_agents WHERE user_agent = 'concurrent-agent'"
        ).fetchone()[0]
        distinct_user_agent_ids = connection.execute(
            "SELECT COUNT(DISTINCT user_agent_id) FROM jobs"
        ).fetchone()[0]
    assert user_agent_count == 1
    assert distinct_user_agent_ids == 1
