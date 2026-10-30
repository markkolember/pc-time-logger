"""SQLite database shared by the PC logger and the Android phone logger.

Both sources write to the same `activity` table and may overlap in time.
Each fills only the columns relevant to it: the PC fills app and file
columns, the phone fills location, distance and cost columns. The phone
never writes this file directly; the PC imports its packets by `id`.
"""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from .timeutil import to_iso, utcnow

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS objects (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    topic       TEXT,
    folder      TEXT UNIQUE,
    address     TEXT,
    lat         REAL,
    lon         REAL,
    radius_m    REAL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rules (
    id           INTEGER PRIMARY KEY,
    pattern_type TEXT NOT NULL CHECK (pattern_type IN ('folder', 'filename')),
    pattern      TEXT NOT NULL,
    object_id    INTEGER NOT NULL REFERENCES objects(id),
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activity (
    id                 TEXT PRIMARY KEY,
    source             TEXT NOT NULL CHECK (source IN ('pc', 'phone')),
    kind               TEXT NOT NULL,
    start_ts           TEXT NOT NULL,
    end_ts             TEXT NOT NULL,
    object_id          INTEGER REFERENCES objects(id),
    object_assigned_by TEXT CHECK (object_assigned_by IN ('auto', 'manual')),
    app                TEXT,
    app_name           TEXT,
    window_title       TEXT,
    file_path          TEXT,
    lat                REAL,
    lon                REAL,
    address            TEXT,
    km                 REAL,
    amount             REAL,
    note               TEXT,
    device_id          TEXT,
    imported_at        TEXT
);

CREATE INDEX IF NOT EXISTS activity_start ON activity(start_ts);
CREATE INDEX IF NOT EXISTS activity_object ON activity(object_id);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()
    return conn


class ActivityStore:
    """Writes PC activity segments."""

    def __init__(self, conn: sqlite3.Connection, device_id: str):
        self.conn = conn
        self.device_id = device_id

    def open_segment(
        self,
        start: datetime,
        app: str,
        app_name: str,
        window_title: str | None,
        file_path: str | None,
    ) -> str:
        row_id = str(uuid.uuid4())
        kind = "file" if file_path else "program"
        with self.conn:
            self.conn.execute(
                """INSERT INTO activity
                   (id, source, kind, start_ts, end_ts, app, app_name, window_title,
                    file_path, device_id, imported_at)
                   VALUES (?, 'pc', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (row_id, kind, to_iso(start), to_iso(start), app, app_name,
                 window_title, file_path, self.device_id, to_iso(utcnow())),
            )
        return row_id

    def set_end(self, row_id: str, end: datetime) -> None:
        with self.conn:
            self.conn.execute("UPDATE activity SET end_ts = ? WHERE id = ?", (to_iso(end), row_id))

    def delete(self, row_id: str) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM activity WHERE id = ?", (row_id,))
