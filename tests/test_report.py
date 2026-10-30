from datetime import datetime, timezone

from pctimelogger import db, report


def add(conn, start, end, app, path=None, source="pc"):
    conn.execute(
        "INSERT INTO activity (id, source, kind, start_ts, end_ts, app, app_name, file_path) VALUES (?,?,?,?,?,?,?,?)",
        (f"{start}{app}", source, "file" if path else "program", start, end, app, app.split(".")[0], path),
    )


def test_totals_clip_and_ignore_phone():
    conn = db.connect(":memory:")
    add(conn, "2026-10-30T07:30:00Z", "2026-10-30T09:00:00Z", "acad.exe", r"C:\o\Audentes pikk koridor\a.dwg")
    add(conn, "2026-10-30T09:00:00Z", "2026-10-30T09:30:00Z", "excel.exe", r"C:\o\b.xlsx")
    add(conn, "2026-10-30T10:00:00Z", "2026-10-30T11:00:00Z", "phone", source="phone")
    start = datetime(2026, 10, 30, 8, 0, tzinfo=timezone.utc)
    end = datetime(2026, 10, 31, 0, 0, tzinfo=timezone.utc)
    t = report.totals(conn, start, end)
    assert t["total"] == 90 * 60
    assert t["by_app"] == {"acad": 3600, "excel": 1800}


def test_format_report_runs():
    conn = db.connect(":memory:")
    add(conn, "2026-10-30T08:00:00Z", "2026-10-30T09:15:00Z", "acad.exe", r"C:\o\Audentes pikk koridor\a.dwg")
    text = report.format_report(conn, datetime(2026, 10, 30).date(), datetime(2026, 10, 30).date())
    assert "a.dwg" in text and "Audentes pikk koridor" in text
    assert report.hm(4500) == "1:15"
