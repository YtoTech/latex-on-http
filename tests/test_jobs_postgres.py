import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
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
        fetched_resources_size=2**40,
        output_size=100_000_000,
    )

    with psycopg.connect(postgres_database) as connection:
        row = connection.execute(
            "SELECT user_agent_id, http_payload_size, fetched_resources_size, "
            "output_size FROM jobs WHERE id = %s",
            (job["id"],),
        ).fetchone()
    assert row == (None, 2**40, 2**40, 100_000_000)


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
