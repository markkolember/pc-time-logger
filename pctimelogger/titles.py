"""Finding a file name or path in a window title.

Examples of titles this handles:
    Autodesk AutoCAD 2024 - [C:\\Objektid\\Audentes pikk koridor\\plaan.dwg]
    Autodesk AutoCAD 2024  plaan.dwg
    Eelarve.xlsx - Excel
    Seletuskiri.docx [Compatibility Mode] - Word
"""

import re

FILE_EXTENSIONS = (
    "dwg", "dxf", "dwt", "dws",
    "xlsx", "xlsm", "xlsb", "xls", "csv",
    "docx", "docm", "doc", "rtf", "txt",
    "pdf", "ifc", "rvt",
)

_EXT = "|".join(FILE_EXTENSIONS)
_PATH_RE = re.compile(
    rf"(?P<path>(?:[A-Za-z]:\\|\\\\)[^<>:\"|?*\[\]]*?\.(?:{_EXT}))(?![\w])",
    re.IGNORECASE,
)
_NAME_RE = re.compile(
    rf"(?P<name>[^\\/:*?\"<>|\[\]]+?\.(?:{_EXT}))(?![\w])",
    re.IGNORECASE,
)
_APP_PREFIX_RE = re.compile(r"^\s*Autodesk AutoCAD[^-\[]*?(?:-\s*|\s{2,}|(?=\[))", re.IGNORECASE)


def find_path(title: str) -> str | None:
    """A full Windows path in the title, if there is one."""
    match = _PATH_RE.search(title or "")
    return match.group("path").strip() if match else None


def find_filename(title: str) -> str | None:
    """A file name (without folder) in the title, if there is one."""
    if not title:
        return None
    path = find_path(title)
    if path:
        return path.rsplit("\\", 1)[-1]
    rest = _APP_PREFIX_RE.sub("", title)
    match = _NAME_RE.search(rest)
    return match.group("name").strip(" -") if match else None
