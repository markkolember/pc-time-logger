"""The logging loop, shared by the command line and the tray app."""

import logging
import socket
import threading
import time

from . import db, phone_import
from .config import Config
from .timeutil import utcnow
from .tracker import Tracker

log = logging.getLogger(__name__)


def run_logging(cfg: Config, stop: threading.Event) -> None:
    """Samples the active window until `stop` is set. Windows only."""
    from .platform_win import WindowsSampler

    conn = db.connect(cfg.db_path)
    tracker = Tracker(db.ActivityStore(conn, socket.gethostname()), cfg)
    sampler = WindowsSampler()
    log.info("Logimine algas, andmebaas: %s", cfg.db_path)
    next_import = 0.0
    try:
        while not stop.is_set():
            try:
                tracker.observe(sampler.sample())
            except Exception:
                log.exception("Proovi lugemine ebaõnnestus")
            if cfg.phone_inbox and time.monotonic() >= next_import:
                next_import = time.monotonic() + cfg.phone_import_seconds
                try:
                    phone_import.import_folder(conn, cfg.phone_inbox)
                except Exception:
                    log.exception("Telefoni andmete import ebaõnnestus")
            stop.wait(cfg.poll_seconds)
    finally:
        tracker.stop(utcnow())
        conn.close()
        log.info("Logimine lõppes")
