from datetime import datetime, timezone
from uuid import uuid4

import pytest
from psycopg.types.json import Jsonb

from latexonhttp.db import jobs


class FakeCursor:
    rowcount = 1

    def __init__(self):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        pass

    def execute(self, query, parameters):
        self.calls.append((query, parameters))

    def fetchone(self):
        return (42,)


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        pass

    def cursor(self):
        return self._cursor


class FakePool:
    def __init__(self, cursor):
        self._connection = FakeConnection(cursor)

    def connection(self):
        return self._connection


def job_metadata(user_agent=None):
    return {
        "id": str(uuid4()),
        "job_status": "received",
        "compiler": "pdflatex",
        "compilation_hash": None,
        "input_spec_mode": "json",
        "http_payload_size": 2**40,
        "cleaned_payload": {"resources": [{"content": True, "file": False}]},
        "remote_ip": "2001:db8::1",
        "forwarded_remote_ip": None,
        "user_agent": user_agent,
        "received_at": datetime.now(timezone.utc),
    }


@pytest.mark.parametrize("user_agent", [None, "", "   "])
def test_create_job_uses_null_foreign_key_without_user_agent(monkeypatch, user_agent):
    cursor = FakeCursor()
    monkeypatch.setattr(jobs, "_get_pool", lambda: FakePool(cursor))

    jobs.create_job(job_metadata(user_agent))

    assert len(cursor.calls) == 1
    query, parameters = cursor.calls[0]
    assert query.startswith("INSERT INTO jobs")
    assert "user_agents" not in query
    assert parameters[jobs._JOB_COLUMNS.index("user_agent_id")] is None
    assert parameters[jobs._JOB_COLUMNS.index("http_payload_size")] == 2**40
    cleaned_payload = parameters[jobs._JOB_COLUMNS.index("cleaned_payload")]
    assert isinstance(cleaned_payload, Jsonb)
    assert cleaned_payload.obj == {"resources": [{"content": True, "file": False}]}


def test_create_job_upserts_a_present_user_agent(monkeypatch):
    cursor = FakeCursor()
    monkeypatch.setattr(jobs, "_get_pool", lambda: FakePool(cursor))

    jobs.create_job(job_metadata("job-test-agent"))

    assert len(cursor.calls) == 2
    assert "ON CONFLICT (user_agent) DO UPDATE" in cursor.calls[0][0]
    assert cursor.calls[0][1] == ("job-test-agent",)
    assert cursor.calls[1][1][jobs._JOB_COLUMNS.index("user_agent_id")] == 42


def test_update_job_binds_values_and_rejects_unknown_columns(monkeypatch):
    cursor = FakeCursor()
    monkeypatch.setattr(jobs, "_get_pool", lambda: FakePool(cursor))
    job_id = str(uuid4())

    jobs.update_job(job_id, job_status="completed", output_size=100_000_000)

    query, parameters = cursor.calls[0]
    assert "job_status = %s" in query
    assert "output_size = %s" in query
    assert parameters == ["completed", 100_000_000, job_id]
    with pytest.raises(ValueError, match="Unsupported job metadata"):
        jobs.update_job(job_id, **{"id; DROP TABLE jobs; --": "invalid"})
