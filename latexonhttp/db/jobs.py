"""PostgreSQL persistence for compilation-job metadata."""

import os
import threading

from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

_JOB_COLUMNS = (
    "id",
    "job_status",
    "compiler",
    "compilation_hash",
    "input_spec_mode",
    "http_payload_size",
    "cleaned_payload",
    "remote_ip",
    "forwarded_remote_ip",
    "user_agent_id",
    "received_at",
)
_UPDATE_COLUMNS = frozenset(
    {
        "job_status",
        "error_code",
        "compilation_hash",
        "started_fetch_at",
        "ended_fetch_at",
        "started_compiling_at",
        "ended_compiling_at",
        "fetched_resources_count",
        "fetched_resources_size",
        "fetched_resources_cache_hits",
        "fetched_resources_cache_hits_size",
        "output_type",
        "output_size",
        "replied_at",
        "completed_at",
    }
)

_pool = None
_pool_lock = threading.Lock()


def _get_pool():
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                database_url = os.getenv("DATABASE_URL") or os.getenv("GOOSE_DBSTRING")
                if not database_url:
                    raise RuntimeError("DATABASE_URL must be configured to track jobs")
                _pool = ConnectionPool(
                    conninfo=database_url,
                    min_size=int(os.getenv("DATABASE_POOL_MIN_SIZE", "1")),
                    max_size=int(os.getenv("DATABASE_POOL_MAX_SIZE", "16")),
                    timeout=float(os.getenv("DATABASE_POOL_TIMEOUT", "10")),
                    open=True,
                )
    return _pool


def _resolve_user_agent_id(cursor, user_agent):
    if user_agent is None or not user_agent.strip():
        return None
    cursor.execute(
        """
        INSERT INTO user_agents (user_agent)
        VALUES (%s)
        ON CONFLICT (user_agent) DO UPDATE SET user_agent = EXCLUDED.user_agent
        RETURNING id
        """,
        (user_agent,),
    )
    return cursor.fetchone()[0]


def create_job(metadata):
    """Insert a job and, when supplied, its user agent in one transaction."""
    metadata = dict(metadata)
    required_columns = set(_JOB_COLUMNS) - {"user_agent_id"}
    missing_columns = required_columns - set(metadata)
    if missing_columns:
        raise ValueError(f"Missing job metadata: {sorted(missing_columns)}")
    metadata["user_agent_id"] = None
    user_agent = metadata.pop("user_agent")
    metadata["cleaned_payload"] = Jsonb(metadata["cleaned_payload"])
    with _get_pool().connection() as connection, connection.cursor() as cursor:
        metadata["user_agent_id"] = _resolve_user_agent_id(cursor, user_agent)
        columns = ", ".join(_JOB_COLUMNS)
        placeholders = ", ".join(["%s"] * len(_JOB_COLUMNS))
        cursor.execute(
            f"INSERT INTO jobs ({columns}) VALUES ({placeholders})",
            [metadata[column] for column in _JOB_COLUMNS],
        )


def update_job(job_id, **metadata):
    """Commit a partial lifecycle update using only explicitly allowed columns."""
    unknown_columns = set(metadata) - _UPDATE_COLUMNS
    if unknown_columns:
        raise ValueError(f"Unsupported job metadata: {sorted(unknown_columns)}")
    if not metadata:
        return
    assignments = ", ".join(f"{column} = %s" for column in metadata)
    with _get_pool().connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE jobs SET {assignments} WHERE id = %s",
            [*metadata.values(), job_id],
        )
        if cursor.rowcount != 1:
            raise RuntimeError(f"Compilation job {job_id} was not found")
