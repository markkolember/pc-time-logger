from datetime import datetime, timedelta, timezone

import pytest

from pctimelogger import db
from pctimelogger.config import Config
from pctimelogger.tracker import Sample, Tracker

T0 = datetime(2026, 10, 30, 8, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def setup():
    conn = db.connect(":memory:")
    cfg = Config(poll_seconds=2, idle_seconds=300, flush_seconds=30, min_seconds=3, db_path=":memory:")
    return conn, Tracker(db.ActivityStore(conn, "PC1"), cfg)


def rows(conn):
    return conn.execute("SELECT * FROM activity ORDER BY start_ts").fetchall()


def feed(tracker, start_s, end_s, step=2, **kw):
    for s in range(start_s, end_s, step):
        tracker.observe(Sample(ts=T0 + timedelta(seconds=s), **kw))


def test_switching_files_makes_segments(setup):
    conn, tr = setup
    feed(tr, 0, 60, app="acad.exe", app_name="AutoCAD", title="a", file_path=r"C:\x\a.dwg")
    feed(tr, 60, 120, app="excel.exe", app_name="Excel", title="b", file_path=r"C:\x\b.xlsx")
    tr.stop(T0 + timedelta(seconds=120))
    r = rows(conn)
    assert [x["file_path"] for x in r] == [r"C:\x\a.dwg", r"C:\x\b.xlsx"]
    assert r[0]["start_ts"] == "2026-10-30T08:00:00Z"
    assert r[0]["end_ts"] == "2026-10-30T08:01:00Z"
    assert r[1]["end_ts"] == "2026-10-30T08:02:00Z"
    assert all(x["source"] == "pc" and x["kind"] == "file" and x["device_id"] == "PC1" for x in r)


def test_short_segments_dropped(setup):
    conn, tr = setup
    feed(tr, 0, 20, app="acad.exe", title="a", file_path="a.dwg")
    feed(tr, 20, 22, app="explorer.exe", title="Explorer")
    feed(tr, 22, 40, app="acad.exe", title="a", file_path="a.dwg")
    tr.stop(T0 + timedelta(seconds=40))
    assert [x["app"] for x in rows(conn)] == ["acad.exe", "acad.exe"]


def test_idle_ends_segment_at_last_input(setup):
    conn, tr = setup
    feed(tr, 0, 60, app="winword.exe", title="d", file_path="d.docx")
    for s in range(60, 400, 2):
        tr.observe(Sample(ts=T0 + timedelta(seconds=s), app="winword.exe", title="d",
                          file_path="d.docx", idle_seconds=s - 60))
    r = rows(conn)
    assert len(r) == 1
    assert r[0]["end_ts"] == "2026-10-30T08:01:00Z"


def test_lock_ends_segment(setup):
    conn, tr = setup
    feed(tr, 0, 60, app="excel.exe", title="b", file_path="b.xlsx")
    tr.observe(Sample(ts=T0 + timedelta(seconds=62), app=None, locked=True))
    feed(tr, 100, 140, app="excel.exe", title="b", file_path="b.xlsx")
    tr.stop(T0 + timedelta(seconds=140))
    r = rows(conn)
    assert len(r) == 2
    assert r[0]["end_ts"] == "2026-10-30T08:01:02Z"
    assert r[1]["start_ts"] == "2026-10-30T08:01:40Z"


def test_sleep_gap_ends_segment_at_last_sample(setup):
    conn, tr = setup
    feed(tr, 0, 60, app="excel.exe", title="b", file_path="b.xlsx")
    feed(tr, 3600, 3620, app="excel.exe", title="b", file_path="b.xlsx")
    tr.stop(T0 + timedelta(seconds=3620))
    r = rows(conn)
    assert len(r) == 2
    assert r[0]["end_ts"] == "2026-10-30T08:00:58Z"


def test_flush_saves_progress(setup):
    conn, tr = setup
    feed(tr, 0, 62, app="excel.exe", title="b", file_path="b.xlsx")
    assert rows(conn)[0]["end_ts"] == "2026-10-30T08:01:00Z"


def test_titles_not_stored_when_disabled(setup):
    conn, tr = setup
    tr.cfg.store_titles = False
    feed(tr, 0, 20, app="chrome.exe", title="Salajane")
    tr.stop(T0 + timedelta(seconds=20))
    r = rows(conn)
    assert r[0]["window_title"] is None and r[0]["kind"] == "program"
