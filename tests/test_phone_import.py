import json

from pctimelogger import db, phone_import


def packet(*events):
    return {"format": "pctimelogger-phone-v1", "device_id": "pixel", "created_ts": "2026-10-30T07:00:00Z",
            "events": list(events)}


STOP = {"id": "e1", "source": "phone", "kind": "stop", "start_ts": "2026-10-30T06:00:00Z",
        "end_ts": "2026-10-30T06:40:00Z", "lat": 59.4, "lon": 24.7, "address": None,
        "object_name": "Audentes", "device_id": "pixel"}


def test_upsert_updates_fields():
    conn = db.connect(":memory:")
    assert phone_import.import_packet(conn, packet(STOP)) == 1
    phone_import.import_packet(conn, packet({**STOP, "address": "Tondi 84a"}))
    rows = conn.execute("SELECT * FROM activity").fetchall()
    assert len(rows) == 1
    assert rows[0]["source"] == "phone" and rows[0]["address"] == "Tondi 84a"
    assert rows[0]["object_name"] == "Audentes"


def test_point_event_and_invalid_skipped():
    conn = db.connect(":memory:")
    refuel = {"id": "e2", "kind": "refuel", "start_ts": "2026-10-30T08:00:00Z", "end_ts": None, "amount": 55.2}
    bad = {"id": "e3", "kind": "teleport", "start_ts": "2026-10-30T08:00:00Z"}
    assert phone_import.import_packet(conn, packet(refuel, bad)) == 1
    row = conn.execute("SELECT * FROM activity").fetchone()
    assert row["end_ts"] == row["start_ts"] and row["device_id"] == "pixel"


def test_folder_import_skips_unchanged(tmp_path):
    conn = db.connect(":memory:")
    (tmp_path / "pixel_20261030_070000.json").write_text(json.dumps(packet(STOP)), encoding="utf-8")
    (tmp_path / "broken.json").write_text("{", encoding="utf-8")
    assert phone_import.import_folder(conn, tmp_path) == 1
    assert phone_import.import_folder(conn, tmp_path) == 0


def test_migration_adds_columns(tmp_path):
    path = tmp_path / "old.db"
    import sqlite3
    old = sqlite3.connect(path)
    v1 = db.SCHEMA.replace("    object_name        TEXT,\n", "").replace("    mode               TEXT,\n", "")
    old.executescript(v1)
    old.close()
    conn = db.connect(path)
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(activity)")}
    assert {"object_name", "mode"} <= cols
