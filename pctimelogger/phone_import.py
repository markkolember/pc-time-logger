"""Imports the phone app's packets from its Google Drive inbox folder.

A packet is <device_id>_<yyyyMMdd_HHmmss>.json:
    {"format": "pctimelogger-phone-v1", "device_id": ..., "created_ts": ...,
     "events": [{"id", "kind", "start_ts", "end_ts", "lat", "lon", ...}]}

The same event id can arrive again with updated fields, so events are
upserted by id. Point events (refuel, cost, work start/end) have no end
time and are stored with end_ts = start_ts.
"""

import json
import logging
import sqlite3
from pathlib import Path

from .timeutil import to_iso, utcnow

log = logging.getLogger(__name__)

FORMAT = "pctimelogger-phone-v1"
KINDS = {"stop", "drive", "work_start", "work_end", "refuel", "cost"}
FIELDS = ("kind", "start_ts", "end_ts", "lat", "lon", "address", "km", "amount",
          "note", "object_name", "mode", "device_id")


def import_packet(conn: sqlite3.Connection, packet: dict) -> int:
    if packet.get("format") != FORMAT:
        raise ValueError(f"unknown packet format: {packet.get('format')!r}")
    now = to_iso(utcnow())
    count = 0
    for event in packet.get("events", []):
        if not event.get("id") or event.get("kind") not in KINDS or not event.get("start_ts"):
            log.warning("Skipping invalid phone event: %s", event)
            continue
        values = {f: event.get(f) for f in FIELDS}
        values["device_id"] = values["device_id"] or packet.get("device_id")
        values["end_ts"] = values["end_ts"] or values["start_ts"]
        conn.execute(
            f"""INSERT INTO activity (id, source, {", ".join(FIELDS)}, imported_at)
                VALUES (:id, 'phone', {", ".join(":" + f for f in FIELDS)}, :imported_at)
                ON CONFLICT(id) DO UPDATE SET
                {", ".join(f"{f} = excluded.{f}" for f in FIELDS)},
                imported_at = excluded.imported_at
                WHERE activity.source = 'phone'""",
            {"id": event["id"], "imported_at": now, **values},
        )
        count += 1
    return count


def import_folder(conn: sqlite3.Connection, folder: str | Path) -> int:
    """Imports new or changed packets in the folder; returns the event count."""
    folder = Path(folder)
    if not folder.is_dir():
        log.warning("Phone inbox not found: %s", folder)
        return 0
    seen = {row["name"]: row["mtime"] for row in conn.execute("SELECT name, mtime FROM imported_files")}
    total = 0
    for path in sorted(folder.glob("*.json")):
        mtime = path.stat().st_mtime
        if seen.get(path.name) == mtime:
            continue
        try:
            packet = json.loads(path.read_text(encoding="utf-8"))
            with conn:
                total += import_packet(conn, packet)
                conn.execute(
                    "INSERT OR REPLACE INTO imported_files (name, mtime, imported_at) VALUES (?, ?, ?)",
                    (path.name, mtime, to_iso(utcnow())),
                )
        except (OSError, ValueError) as exc:
            log.warning("Could not import %s: %s", path.name, exc)
    return total
