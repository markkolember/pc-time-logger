"""Settings, read from config.json in the app data folder."""

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

APP_DIR_NAME = "PCTimeLogger"


def data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    return Path(base) / APP_DIR_NAME


def config_path() -> Path:
    return data_dir() / "config.json"


@dataclass
class Config:
    # Seconds between samples of the active window.
    poll_seconds: float = 2.0
    # No mouse or keyboard input for this long counts as idle time.
    idle_seconds: float = 300.0
    # How often the open segment's end time is saved, so a crash loses little.
    flush_seconds: float = 30.0
    # Segments shorter than this (e.g. alt-tabbing past a window) are dropped.
    min_seconds: float = 3.0
    # Save window titles; turn off to keep only program and file.
    store_titles: bool = True
    # Folder holding the active object folders, e.g. D:\AAA aktiivsed objektid.
    objects_root: str = ""
    db_path: str = field(default_factory=lambda: str(data_dir() / "timelog.db"))

    @property
    def gap_seconds(self) -> float:
        """A pause between samples longer than this means the PC slept."""
        return max(self.poll_seconds * 5, 30.0)


def load_config(path: Path | None = None) -> Config:
    path = path or config_path()
    cfg = Config()
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        known = {f.name for f in fields(Config)}
        for key, value in data.items():
            if key in known:
                setattr(cfg, key, value)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(cfg), indent=2, ensure_ascii=False), encoding="utf-8")
    return cfg
