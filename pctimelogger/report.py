"""Text reports: time per program and per file for a date range."""

import ntpath
import sqlite3
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from .timeutil import from_iso, to_iso


def local_range(first: date, last: date) -> tuple[datetime, datetime]:
    start = datetime.combine(first, time.min).astimezone()
    end = datetime.combine(last + timedelta(days=1), time.min).astimezone()
    return start, end


def segments(conn: sqlite3.Connection, start: datetime, end: datetime, source: str = "pc"):
    """Rows overlapping [start, end), with start and end clipped to the range."""
    rows = conn.execute(
        """SELECT * FROM activity
           WHERE source = ? AND start_ts < ? AND end_ts > ?
           ORDER BY start_ts""",
        (source, to_iso(end), to_iso(start)),
    ).fetchall()
    for row in rows:
        s = max(from_iso(row["start_ts"]), start)
        e = min(from_iso(row["end_ts"]), end)
        if e > s:
            yield row, s, e


def totals(conn: sqlite3.Connection, start: datetime, end: datetime) -> dict:
    by_app: dict[str, float] = defaultdict(float)
    by_file: dict[tuple[str, str], float] = defaultdict(float)
    total = 0.0
    for row, s, e in segments(conn, start, end):
        seconds = (e - s).total_seconds()
        total += seconds
        by_app[row["app_name"] or row["app"]] += seconds
        if row["file_path"]:
            by_file[(row["app_name"] or row["app"], row["file_path"])] += seconds
    return {"total": total, "by_app": dict(by_app), "by_file": dict(by_file)}


def hm(seconds: float) -> str:
    minutes = int(round(seconds / 60))
    return f"{minutes // 60}:{minutes % 60:02d}"


def format_report(conn: sqlite3.Connection, first: date, last: date, top: int = 20) -> str:
    start, end = local_range(first, last)
    t = totals(conn, start, end)
    period = first.isoformat() if first == last else f"{first.isoformat()} – {last.isoformat()}"
    lines = [f"Aruanne {period}", f"Aktiivne aeg kokku: {hm(t['total'])}", "", "Programmid:"]
    for name, sec in sorted(t["by_app"].items(), key=lambda kv: -kv[1])[:top]:
        lines.append(f"  {hm(sec):>6}  {name}")
    lines += ["", "Failid:"]
    if not t["by_file"]:
        lines.append("  (pole)")
    for (app, path), sec in sorted(t["by_file"].items(), key=lambda kv: -kv[1])[:top]:
        folder = ntpath.basename(ntpath.dirname(path))
        name = ntpath.basename(path)
        where = f"  ({folder})" if folder else ""
        lines.append(f"  {hm(sec):>6}  {name}{where}  [{app}]")
    return "\n".join(lines)


def format_timeline(conn: sqlite3.Connection, day: date) -> str:
    start, end = local_range(day, day)
    lines = [f"Ajajoon {day.isoformat()}"]
    for row, s, e in segments(conn, start, end):
        what = row["file_path"] or row["window_title"] or ""
        what = ntpath.basename(what) if row["file_path"] else what
        lines.append(
            f"  {s.astimezone():%H:%M}–{e.astimezone():%H:%M}  {hm((e - s).total_seconds()):>5}  "
            f"{row['app_name'] or row['app']}  {what}"
        )
    return "\n".join(lines)
