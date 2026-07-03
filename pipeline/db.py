"""SQLite access + verbatim response cache. Shared infrastructure, not a stage.

The cache is the architecture, not politeness (music-project.md): every stage is
re-runnable from cached data, so raw responses are stored before any transform.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone

import config


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(config.SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def cache_key(source: str, endpoint: str, params: dict) -> str:
    """Stable key over sorted params (API key excluded by callers)."""
    canonical = json.dumps(params, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:16]
    return f"{source}:{endpoint}:{digest}"


def cache_get(conn: sqlite3.Connection, key: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM raw_responses WHERE cache_key = ?", (key,)
    ).fetchone()


def cache_put(
    conn: sqlite3.Connection,
    key: str,
    source: str,
    endpoint: str,
    params: dict,
    status_code: int | None,
    body: str | None,
) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO raw_responses
           (cache_key, source, endpoint, params, status_code, body, fetched_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            key,
            source,
            endpoint,
            json.dumps(params, sort_keys=True, ensure_ascii=False),
            status_code,
            body,
            utcnow(),
        ),
    )
    conn.commit()
