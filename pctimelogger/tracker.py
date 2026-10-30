"""Turns a stream of window samples into activity segments.

A segment is continuous work in one program on one file (or one window
title when the file is unknown). A segment ends when the window or file
changes, the user goes idle, the PC is locked, or the PC sleeps.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from .config import Config
from .db import ActivityStore


@dataclass
class Sample:
    ts: datetime
    app: str | None
    app_name: str | None = None
    title: str | None = None
    file_path: str | None = None
    idle_seconds: float = 0.0
    locked: bool = False

    @property
    def key(self) -> tuple[str | None, str | None]:
        return (self.app, self.file_path or self.title)


@dataclass
class _Segment:
    row_id: str
    key: tuple[str | None, str | None]
    start: datetime
    last_seen: datetime
    last_flush: datetime


class Tracker:
    def __init__(self, store: ActivityStore, cfg: Config):
        self.store = store
        self.cfg = cfg
        self.current: _Segment | None = None

    def observe(self, sample: Sample) -> None:
        now = sample.ts
        cur = self.current

        if cur and (now - cur.last_seen).total_seconds() > self.cfg.gap_seconds:
            self._close(cur.last_seen)
            cur = None

        idle = sample.idle_seconds >= self.cfg.idle_seconds
        if sample.locked or idle or not sample.app:
            if cur:
                end = now - timedelta(seconds=sample.idle_seconds) if idle else now
                self._close(max(cur.start, min(end, now)))
            return

        if cur and cur.key == sample.key:
            cur.last_seen = now
            if (now - cur.last_flush).total_seconds() >= self.cfg.flush_seconds:
                self.store.set_end(cur.row_id, now)
                cur.last_flush = now
            return

        if cur:
            self._close(now)
        title = sample.title if self.cfg.store_titles else None
        row_id = self.store.open_segment(now, sample.app, sample.app_name or sample.app, title, sample.file_path)
        self.current = _Segment(row_id, sample.key, now, now, now)

    def stop(self, now: datetime) -> None:
        if self.current:
            self._close(min(now, self.current.last_seen + timedelta(seconds=self.cfg.poll_seconds)))

    def _close(self, end: datetime) -> None:
        cur = self.current
        self.current = None
        if cur is None:
            return
        if (end - cur.start).total_seconds() < self.cfg.min_seconds:
            self.store.delete(cur.row_id)
        else:
            self.store.set_end(cur.row_id, end)
