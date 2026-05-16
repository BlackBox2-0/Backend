from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

try:
    import psycopg
except ImportError:  # pragma: no cover - optional when running SQLite only
    psycopg = None


DEFAULT_DATABASE_PATH = Path(__file__).with_name("blackbox.db")
POSTGRES_SCHEME_PREFIXES = ("postgres://", "postgresql://")
TABLES = (
    "collected_events",
    "activity_observations",
    "productivity_detections",
    "policy_evaluations",
    "enforcement_events",
    "audit_log",
    "orchestration_runs",
    "incident_actions",
    "overrides",
)
CREATE_TABLE_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS collected_events (
        id TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        "user" TEXT NOT NULL,
        role TEXT NOT NULL,
        department TEXT NOT NULL,
        action TEXT NOT NULL,
        resource TEXT NOT NULL,
        context TEXT,
        event_timestamp TEXT,
        received_at TEXT NOT NULL,
        raw_event_json TEXT NOT NULL,
        payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS activity_observations (
        id TEXT PRIMARY KEY,
        event_id TEXT NOT NULL,
        source TEXT NOT NULL,
        "user" TEXT NOT NULL,
        role TEXT NOT NULL,
        department TEXT NOT NULL,
        action TEXT NOT NULL,
        resource TEXT NOT NULL,
        system TEXT NOT NULL,
        event_timestamp TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS productivity_detections (
        id TEXT PRIMARY KEY,
        "user" TEXT NOT NULL,
        decision TEXT NOT NULL,
        score REAL NOT NULL,
        observed_at TEXT NOT NULL,
        payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS policy_evaluations (
        id TEXT PRIMARY KEY,
        event_id TEXT NOT NULL,
        run_id TEXT NOT NULL,
        model_recommendation TEXT NOT NULL,
        policy_rule_matched TEXT,
        final_decision TEXT NOT NULL,
        final_decision_source TEXT NOT NULL,
        policy_version TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS enforcement_events (
        id TEXT PRIMARY KEY,
        event_type TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        "user" TEXT NOT NULL,
        resource TEXT NOT NULL,
        analyst_decision TEXT NOT NULL,
        final_decision TEXT NOT NULL,
        requires_human_approval INTEGER NOT NULL,
        payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_log (
        id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        audit_type TEXT,
        "user" TEXT NOT NULL,
        role TEXT NOT NULL,
        department TEXT NOT NULL,
        action TEXT NOT NULL,
        resource TEXT NOT NULL,
        risk_score REAL NOT NULL,
        decision TEXT NOT NULL,
        analyst_decision TEXT,
        requires_human_approval INTEGER,
        payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS orchestration_runs (
        id TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        "user" TEXT NOT NULL,
        action TEXT NOT NULL,
        resource TEXT NOT NULL,
        completed_at TEXT NOT NULL,
        payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS incident_actions (
        id TEXT PRIMARY KEY,
        action_type TEXT NOT NULL,
        status TEXT NOT NULL,
        incident_title TEXT NOT NULL,
        incident_type TEXT NOT NULL,
        affected_user TEXT NOT NULL,
        department TEXT NOT NULL,
        resource TEXT NOT NULL,
        requested_by TEXT NOT NULL,
        assigned_to_id TEXT,
        created_at TEXT NOT NULL,
        payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS overrides (
        id TEXT PRIMARY KEY,
        original_event_id TEXT NOT NULL,
        actor TEXT NOT NULL,
        role TEXT NOT NULL,
        reason TEXT NOT NULL,
        new_decision TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
)


def get_database_path() -> str:
    return os.getenv("DATABASE_PATH", str(DEFAULT_DATABASE_PATH))


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", f"sqlite:///{get_database_path()}")


def get_database_backend() -> str:
    return "postgres" if is_postgres() else "sqlite"


def get_database_target() -> str:
    if is_postgres():
        return _masked_database_url(get_database_url())
    return get_database_path()


def is_postgres() -> bool:
    return get_database_url().startswith(POSTGRES_SCHEME_PREFIXES)


def _sqlite_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(get_database_path())
    connection.row_factory = sqlite3.Row
    return connection


def _postgres_connection():
    if psycopg is None:
        raise RuntimeError(
            "psycopg is not installed. Add it to requirements and rebuild the backend image to use PostgreSQL."
        )
    return psycopg.connect(get_database_url())


def get_connection():
    if is_postgres():
        return _postgres_connection()
    return _sqlite_connection()


def init_db() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            for statement in CREATE_TABLE_STATEMENTS:
                cursor.execute(statement)
        connection.commit()


def next_id(table: str, prefix: str) -> str:
    init_db()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {quote_ident(table)}")
            count = cursor.fetchone()[0]
    return f"{prefix}-{count + 1}"


def insert_record(table: str, payload: dict[str, Any]) -> None:
    init_db()
    columns = ", ".join(quote_ident(column) for column in payload.keys())
    placeholders = ", ".join([placeholder_token()] * len(payload))
    values = [payload[key] for key in payload]

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {quote_ident(table)} ({columns}) VALUES ({placeholders})",
                values,
            )
        connection.commit()


def update_record(table: str, record_id: str, payload: dict[str, Any]) -> None:
    init_db()
    assignments = ", ".join(f"{quote_ident(column)} = {placeholder_token()}" for column in payload.keys())
    values = [payload[key] for key in payload]
    values.append(record_id)

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE {quote_ident(table)} SET {assignments} WHERE {quote_ident('id')} = {placeholder_token()}",
                values,
            )
        connection.commit()


def fetch_all(table: str, order_by: str = "id DESC") -> list[dict[str, Any]]:
    init_db()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {quote_ident(table)} ORDER BY {quote_order_by(order_by)}")
            rows = cursor.fetchall()
            if not rows:
                return []
            columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


def clear_all_tables() -> None:
    init_db()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            for table in TABLES:
                cursor.execute(f"DELETE FROM {quote_ident(table)}")
        connection.commit()


def placeholder_token() -> str:
    return "%s" if is_postgres() else "?"


def dump_json(value: Any) -> str:
    return json.dumps(value, default=str)


def load_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    return json.loads(value)


def _masked_database_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.password is None:
        return value

    auth = parsed.username or ""
    if auth:
        auth = f"{auth}:***"
    netloc = f"{auth}@{parsed.hostname or ''}"
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def quote_ident(identifier: str) -> str:
    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'


def quote_order_by(value: str) -> str:
    parts = value.split()
    if not parts:
        return quote_ident("id")
    direction = parts[1].upper() if len(parts) > 1 else ""
    if direction not in {"", "ASC", "DESC"}:
        direction = ""
    column = quote_ident(parts[0])
    return f"{column} {direction}".strip()


init_db()
