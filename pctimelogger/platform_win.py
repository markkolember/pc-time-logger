"""Windows: the active window, its program and file, idle time and lock state."""

import ctypes
import ctypes.wintypes as wt
import logging
import os

import psutil
import pythoncom
import win32api
import win32com.client
import win32gui
import win32process

from . import titles
from .timeutil import utcnow
from .tracker import Sample

log = logging.getLogger(__name__)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
user32.OpenInputDesktop.restype = wt.HANDLE
user32.SwitchDesktop.argtypes = [wt.HANDLE]
user32.CloseDesktop.argtypes = [wt.HANDLE]

DESKTOP_SWITCHDESKTOP = 0x0100

# Programs that can tell us their active document's full path over COM.
COM_DOCUMENTS = {
    "excel.exe": ("Excel.Application", "ActiveWorkbook"),
    "winword.exe": ("Word.Application", "ActiveDocument"),
    "acad.exe": ("AutoCAD.Application", "ActiveDocument"),
}


class _LastInputInfo(ctypes.Structure):
    _fields_ = [("cbSize", wt.UINT), ("dwTime", wt.DWORD)]


def idle_seconds() -> float:
    info = _LastInputInfo()
    info.cbSize = ctypes.sizeof(info)
    if not user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    return ((kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000.0


def is_locked() -> bool:
    desk = user32.OpenInputDesktop(0, False, DESKTOP_SWITCHDESKTOP)
    if not desk:
        return True
    try:
        return not user32.SwitchDesktop(desk)
    finally:
        user32.CloseDesktop(desk)


def _file_description(exe_path: str) -> str | None:
    try:
        lang, codepage = win32api.GetFileVersionInfo(exe_path, "\\VarFileInfo\\Translation")[0]
        key = f"\\StringFileInfo\\{lang:04x}{codepage:04x}\\FileDescription"
        return win32api.GetFileVersionInfo(exe_path, key) or None
    except Exception:
        return None


class WindowsSampler:
    def __init__(self):
        pythoncom.CoInitialize()
        self._app_names: dict[str, str] = {}
        self._files: dict[tuple[int, str], str | None] = {}

    def sample(self) -> Sample:
        now = utcnow()
        idle = idle_seconds()
        if is_locked():
            return Sample(ts=now, app=None, idle_seconds=idle, locked=True)

        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return Sample(ts=now, app=None, idle_seconds=idle)
        title = win32gui.GetWindowText(hwnd)
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            exe_path = proc.exe()
        except (psutil.Error, OSError):
            return Sample(ts=now, app=None, title=title, idle_seconds=idle)

        app = os.path.basename(exe_path).lower()
        return Sample(
            ts=now,
            app=app,
            app_name=self._app_name(app, exe_path),
            title=title,
            file_path=self._file_path(proc, app, title),
            idle_seconds=idle,
        )

    def _app_name(self, app: str, exe_path: str) -> str:
        if app not in self._app_names:
            self._app_names[app] = _file_description(exe_path) or os.path.splitext(app)[0]
        return self._app_names[app]

    def _file_path(self, proc: psutil.Process, app: str, title: str) -> str | None:
        key = (proc.pid, title)
        if key not in self._files:
            if len(self._files) > 500:
                self._files.clear()
            self._files[key] = self._resolve_file(proc, app, title)
        return self._files[key]

    def _resolve_file(self, proc: psutil.Process, app: str, title: str) -> str | None:
        name = titles.find_filename(title)

        com_path = self._com_document(app)
        if com_path and (not name or os.path.basename(com_path).lower() == name.lower()):
            return com_path

        path = titles.find_path(title)
        if path:
            return path

        if name:
            try:
                for f in proc.open_files():
                    if os.path.basename(f.path).lower() == name.lower():
                        return f.path
            except (psutil.Error, OSError):
                pass
            return name
        return None

    @staticmethod
    def _com_document(app: str) -> str | None:
        if app not in COM_DOCUMENTS:
            return None
        prog_id, attr = COM_DOCUMENTS[app]
        try:
            doc = getattr(win32com.client.GetActiveObject(prog_id), attr)
            return str(doc.FullName) if doc is not None else None
        except Exception as exc:
            log.debug("COM lookup for %s failed: %s", app, exc)
            return None
