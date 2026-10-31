"""Self-install: the exe copies itself over the previous installation.

Running PCTimeLogger.exe from anywhere else (e.g. Downloads) stops the
running logger, replaces the installed exe, adds a Start menu shortcut
and starts the installed copy. Data and settings in %LOCALAPPDATA%\\PCTimeLogger
are kept.
"""

import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import psutil

log = logging.getLogger(__name__)

EXE_NAME = "PCTimeLogger.exe"
MUTEX_NAME = "Local\\PCTimeLogger"
QUIT_EVENT_NAME = "Local\\PCTimeLogger-quit"


def install_dir() -> Path:
    return Path(os.environ["LOCALAPPDATA"]) / "Programs" / "PCTimeLogger"


def installed_exe() -> Path:
    return install_dir() / EXE_NAME


def is_installed_copy() -> bool:
    return Path(sys.executable).resolve() == installed_exe().resolve()


def stop_running(timeout: float = 15.0) -> None:
    """Asks the running logger to quit, then makes sure older versions are gone."""
    import win32event

    event = win32event.CreateEvent(None, True, False, QUIT_EVENT_NAME)
    win32event.SetEvent(event)

    me = os.getpid()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and _old_processes(me):
        time.sleep(0.5)
    for proc in _old_processes(me):
        log.info("Lõpetan vana protsessi %s", proc.pid)
        try:
            proc.kill()
        except psutil.Error:
            pass
    win32event.ResetEvent(event)


def _old_processes(me: int) -> list[psutil.Process]:
    """The installed exe, and the earlier `pythonw -m pctimelogger run` setup."""
    found = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        if proc.pid == me:
            continue
        name = (proc.info["name"] or "").lower()
        cmdline = " ".join(proc.info["cmdline"] or []).lower()
        if name == EXE_NAME.lower() or ("pythonw" in name and "pctimelogger" in cmdline):
            found.append(proc)
    return found


def _copy_self(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(20):
        try:
            shutil.copy2(sys.executable, target)
            return
        except PermissionError:
            time.sleep(0.5)
    raise RuntimeError(f"Ei saanud üle kirjutada: {target}")


def _start_menu_shortcut(target: Path) -> None:
    import win32com.client

    programs = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    shell = win32com.client.Dispatch("WScript.Shell")
    link = shell.CreateShortCut(str(programs / "PC ajalogija.lnk"))
    link.TargetPath = str(target)
    link.WorkingDirectory = str(target.parent)
    link.IconLocation = str(target)
    link.Save()


def _remove_old_startup_shortcuts() -> None:
    """Removes Startup-folder shortcuts to the earlier start.bat."""
    import win32com.client

    startup = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    shell = win32com.client.Dispatch("WScript.Shell")
    for lnk in startup.glob("*.lnk"):
        target = Path(shell.CreateShortCut(str(lnk)).TargetPath or "")
        if target.name.lower() == "start.bat" and (target.parent / "pctimelogger").is_dir():
            log.info("Eemaldan vana automaatkäivituse otsetee %s", lnk)
            lnk.unlink(missing_ok=True)


def install_and_launch() -> None:
    target = installed_exe()
    log.info("Paigaldan %s -> %s", sys.executable, target)
    stop_running()
    _copy_self(target)
    try:
        _start_menu_shortcut(target)
        _remove_old_startup_shortcuts()
    except Exception:
        log.exception("Otseteede seadistamine ebaõnnestus")
    subprocess.Popen([str(target), "--installed"], close_fds=True)
