import json
from datetime import datetime

from pctimelogger import analysis, db, phone_import
from pctimelogger.config import Config


def add_pc(conn, rid, start, end, path, app="AutoCAD"):
    conn.execute(
        "INSERT INTO activity (id, source, kind, start_ts, end_ts, app, app_name, file_path) VALUES (?, 'pc', 'file', ?, ?, 'acad.exe', ?, ?)",
        (rid, start, end, app, path),
    )


def test_build_data_links_pc_phone_and_drives():
    conn = db.connect(":memory:")
    base = r"D:\AAA aktiivsed objektid"
    add_pc(conn, "a", "2026-11-03T08:00:00Z", "2026-11-03T09:00:00Z", base + r"\Audentes pikk koridor\plaan.dwg")
    add_pc(conn, "b", "2026-11-03T09:00:00Z", "2026-11-03T09:30:00Z", base + r"\Audentes naiste duširuum\tabel.xlsx", "Excel")
    phone_import.import_packet(conn, {"format": "pctimelogger-phone-v1", "device_id": "tel", "events": [
        {"id": "d1", "kind": "drive", "start_ts": "2026-11-03T10:00:00Z", "end_ts": "2026-11-03T10:30:00Z", "km": 22.0, "mode": "car"},
        {"id": "s1", "kind": "stop", "start_ts": "2026-11-03T10:31:00Z", "end_ts": "2026-11-03T12:31:00Z",
         "object_name": "Audentes pikk koridor", "address": "Tondi 84a"},
        {"id": "d2", "kind": "drive", "start_ts": "2026-11-03T12:32:00Z", "end_ts": "2026-11-03T13:00:00Z", "km": 21.0},
        {"id": "s2", "kind": "stop", "start_ts": "2026-11-03T13:01:00Z", "end_ts": "2026-11-03T14:00:00Z", "address": "Kodu"},
    ]})
    data = analysis.build_data(conn, Config(db_path=":memory:"))
    rows = [dict(zip(data["fields"], r)) for r in data["rows"]]

    def total(**kw):
        return sum(r["seconds"] for r in rows if all(r[k] == v for k, v in kw.items()))

    assert total(source="pc", object="Audentes") == 90 * 60
    assert total(source="pc", topic="pikk koridor") == 3600
    assert total(source="site", object="Audentes", topic="pikk koridor") == 2 * 3600
    assert total(source="drive", object="Audentes") == 58 * 60
    assert round(sum(r["km"] for r in rows if r["source"] == "drive")) == 43
    assert total(source="site", object="") == 59 * 60


def test_render_html_embeds_data():
    data = {"fields": ["day"], "rows": [["2026-11-03"]]}
    html = analysis.render_html(data, datetime(2026, 11, 3, 20, 0))
    payload = html.split("const DATA = ", 1)[1].split(";\n", 1)[0]
    assert json.loads(payload) == data
    assert "{{GENERATED}}" not in html


def test_split_by_day_over_midnight():
    from datetime import timezone
    s = datetime(2026, 11, 3, 23, 0).astimezone()
    e = datetime(2026, 11, 4, 1, 0).astimezone()
    parts = list(analysis._split_by_day(s, e))
    assert [p[1] for p in parts] == [3600, 3600]
