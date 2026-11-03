"""Analysis page: time per object, topic, folder and file, with on-site time from the phone.

The page is a single HTML file opened in the browser. Data is aggregated per
local day and embedded as JSON, so the period can be changed on the page.
"""

import json
import ntpath
import sqlite3
from collections import defaultdict
from datetime import datetime, time, timedelta
from importlib import resources

from . import objects
from .config import Config
from .timeutil import from_iso

# A stop starting this many seconds from a drive's end is where the drive went.
DRIVE_STOP_GAP = 600


def _split_by_day(start: datetime, end: datetime):
    """Yields (local date, seconds) for each local day the span covers."""
    s, e = start.astimezone(), end.astimezone()
    while s < e:
        next_day = datetime.combine(s.date() + timedelta(days=1), time.min).astimezone()
        part_end = min(e, next_day)
        yield s.date(), (part_end - s).total_seconds()
        s = part_end


def build_data(conn: sqlite3.Connection, cfg: Config) -> dict:
    rows = conn.execute(
        "SELECT * FROM activity WHERE kind IN ('file', 'program', 'stop', 'drive') ORDER BY start_ts"
    ).fetchall()

    folders = objects.list_project_folders(cfg.objects_root)
    for row in rows:
        folder = objects.project_folder(row["file_path"], cfg.objects_root)
        if folder:
            folders.add(folder)
    names = objects.split_names(folders)
    by_lower = {f.lower(): names[f] for f in folders}
    object_names = {obj.lower(): obj for obj, _ in names.values()}

    def place(object_name: str | None) -> tuple[str, str]:
        if not object_name:
            return "", ""
        key = object_name.strip().lower()
        if key in by_lower:
            return by_lower[key]
        return object_names.get(key, object_name.strip()), ""

    # A drive belongs to the object it leads to, or else to the one it leaves from.
    stops = [(from_iso(r["start_ts"]), from_iso(r["end_ts"]), place(r["object_name"]))
             for r in rows if r["source"] == "phone" and r["kind"] == "stop"]

    def stop_near(ts: datetime, edge: int) -> tuple[str, str]:
        for stop in stops:
            if abs((stop[edge] - ts).total_seconds()) <= DRIVE_STOP_GAP and stop[2][0]:
                return stop[2]
        return "", ""

    def drive_place(row) -> tuple[str, str]:
        to = stop_near(from_iso(row["end_ts"]), 0)
        return to if to[0] else stop_near(from_iso(row["start_ts"]), 1)

    agg: dict[tuple, list] = defaultdict(lambda: [0.0, 0, None, None, 0.0])
    for row in rows:
        start, end = from_iso(row["start_ts"]), from_iso(row["end_ts"])
        if end <= start:
            continue
        if row["source"] == "pc":
            path = row["file_path"]
            project = objects.project_folder(path, cfg.objects_root)
            obj, topic = names.get(project, ("", "")) if project else ("", "")
            key_rest = (
                "pc",
                obj,
                topic,
                project or objects.parent_folder(path) or "",
                ntpath.basename(path) if path else "",
                path or "",
                row["app_name"] or row["app"] or "",
            )
        elif row["kind"] == "stop":
            obj, topic = place(row["object_name"])
            key_rest = ("site", obj, topic or ("" if obj else row["address"] or ""), "", "", "", row["address"] or "")
        else:
            obj, topic = drive_place(row)
            key_rest = ("drive", obj, topic, "", "", "", row["mode"] or "")
        days = list(_split_by_day(start, end))
        total = sum(sec for _, sec in days) or 1
        for i, (day, sec) in enumerate(days):
            a = agg[(day.isoformat(),) + key_rest]
            a[0] += sec
            a[1] += 1 if i == 0 else 0
            a[2] = row["start_ts"] if a[2] is None else min(a[2], row["start_ts"])
            a[3] = row["end_ts"] if a[3] is None else max(a[3], row["end_ts"])
            a[4] += (row["km"] or 0) * sec / total

    return {
        "fields": ["day", "source", "object", "topic", "folder", "file", "path", "detail",
                   "seconds", "count", "first", "last", "km"],
        "rows": [list(k) + [round(v[0]), v[1], v[2], v[3], round(v[4], 2)] for k, v in agg.items()],
    }


def render_html(data: dict, generated: datetime) -> str:
    template = resources.files("pctimelogger").joinpath("analysis.html").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return (template
            .replace("/*DATA*/null", payload)
            .replace("{{GENERATED}}", generated.astimezone().strftime("%d.%m.%Y %H:%M")))
