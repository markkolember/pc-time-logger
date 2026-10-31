"""The tray app that PCTimeLogger.exe runs: logs in the background, shows reports."""

import ctypes
import logging
import os
import sys
import threading
from datetime import date, timedelta

from . import autostart, db, installer, report
from .config import config_path, data_dir, load_config, save_config
from .icon import icon_image
from .service import run_logging

log = logging.getLogger(__name__)

TITLE = "PC ajalogija"


def _message(text: str) -> None:
    ctypes.windll.user32.MessageBoxW(None, text, TITLE, 0x40)


def _open_report(first: date, last: date) -> None:
    cfg = load_config()
    conn = db.connect(cfg.db_path)
    try:
        text = report.format_report(conn, first, last)
        if first == last:
            text += "\n\n" + report.format_timeline(conn, first)
    finally:
        conn.close()
    path = data_dir() / "aruanne.txt"
    path.write_text(text, encoding="utf-8-sig")
    os.startfile(path)


def _watch_quit_event(on_quit) -> None:
    import win32event

    event = win32event.CreateEvent(None, True, False, installer.QUIT_EVENT_NAME)
    win32event.WaitForSingleObject(event, win32event.INFINITE)
    on_quit()


def run_tray() -> int:
    import pystray
    import win32api
    import win32event
    import winerror

    first_run = not config_path().exists()
    cfg = load_config()

    mutex = win32event.CreateMutex(None, False, installer.MUTEX_NAME)
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        _message("PC ajalogija juba töötab.\n\nIkoon on tegumiriba paremas nurgas, kellaaja kõrval.")
        return 0

    if cfg.autostart:
        autostart.enable()

    stop = threading.Event()
    worker = threading.Thread(target=run_logging, args=(cfg, stop), name="logger", daemon=True)
    worker.start()

    def today(icon, item):
        _open_report(date.today(), date.today())

    def week(icon, item):
        t = date.today()
        first = t - timedelta(days=t.weekday())
        _open_report(first, first + timedelta(days=6))

    def open_folder(icon, item):
        os.startfile(data_dir())

    def toggle_autostart(icon, item):
        cfg.autostart = not cfg.autostart
        (autostart.enable if cfg.autostart else autostart.disable)()
        save_config(cfg)

    def quit_app(icon=None, item=None):
        stop.set()
        icon_ref.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Tänane aruanne", today, default=True),
        pystray.MenuItem("Selle nädala aruanne", week),
        pystray.MenuItem("Ava andmete kaust", open_folder),
        pystray.MenuItem("Käivita koos Windowsiga", toggle_autostart, checked=lambda item: cfg.autostart),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Välju", quit_app),
    )
    icon_ref = pystray.Icon("PCTimeLogger", icon_image(), f"{TITLE}: logimine käib", menu)
    threading.Thread(target=_watch_quit_event, args=(quit_app,), daemon=True).start()

    def on_ready(icon):
        icon.visible = True
        if first_run or "--installed" in sys.argv:
            icon.notify("Logimine käib taustal. Aruande näed, kui klõpsad sellel ikoonil.", TITLE)

    icon_ref.run(setup=on_ready)
    stop.set()
    worker.join(timeout=10)
    del mutex
    return 0


def main() -> int:
    if getattr(sys, "frozen", False) and not installer.is_installed_copy():
        try:
            installer.install_and_launch()
        except Exception as exc:
            log.exception("Paigaldamine ebaõnnestus")
            _message(f"Paigaldamine ebaõnnestus:\n{exc}")
            return 1
        return 0
    return run_tray()
