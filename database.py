import json
import sqlite3
from contextlib import contextmanager
from typing import Any
from backend.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS incidents (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, api_name TEXT NOT NULL, method TEXT NOT NULL,
 endpoint TEXT NOT NULL, status_code INTEGER, error_message TEXT NOT NULL,
 request_metadata TEXT NOT NULL, response_metadata TEXT NOT NULL, headers TEXT NOT NULL,
 request_sample TEXT NOT NULL, response_sample TEXT NOT NULL, duration_ms REAL,
 timestamp TEXT, logs TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'Unknown / other',
 confidence REAL NOT NULL DEFAULT 0.2, status TEXT NOT NULL DEFAULT 'open',
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS diagnoses (
 id INTEGER PRIMARY KEY AUTOINCREMENT, incident_id TEXT NOT NULL, created_at TEXT NOT NULL,
 result TEXT NOT NULL, FOREIGN KEY(incident_id) REFERENCES incidents(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS fixes (
 id INTEGER PRIMARY KEY AUTOINCREMENT, incident_id TEXT NOT NULL, created_at TEXT NOT NULL,
 notes TEXT NOT NULL, outcome TEXT NOT NULL, FOREIGN KEY(incident_id) REFERENCES incidents(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS documents (
 id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT NOT NULL, source_ref TEXT NOT NULL,
 passage TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scenarios (
 id INTEGER PRIMARY KEY AUTOINCREMENT, incident_id TEXT NOT NULL, created_at TEXT NOT NULL,
 name TEXT NOT NULL, expected_status INTEGER, observed_status INTEGER,
 input_sample TEXT NOT NULL, result TEXT NOT NULL, notes TEXT NOT NULL,
 FOREIGN KEY(incident_id) REFERENCES incidents(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_incidents_created ON incidents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_status_category ON incidents(status, category);
CREATE INDEX IF NOT EXISTS idx_documents_filename ON documents(filename);
"""


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(SCHEMA)


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def encode(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def decode(value: str, fallback: Any = None) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback
