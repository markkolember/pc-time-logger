"""Linking files to objects and topics by their folder.

A file under ...\\AAA aktiivsed objektid\\Audentes pikk koridor\\... belongs to
the project folder "Audentes pikk koridor". The object is the start of the
folder name that other project folders share ("Audentes"), the topic is the
rest ("pikk koridor"). Object names can be one or two words.
"""

import ntpath
import os

ROOT_MARKER = "aktiivsed objektid"


def _parts(path: str) -> list[str]:
    drive, rest = ntpath.splitdrive(path)
    return [p for p in rest.replace("/", "\\").split("\\") if p]


def project_folder(path: str | None, objects_root: str = "") -> str | None:
    """The project folder a file belongs to, or None if it is not in one."""
    if not path:
        return None
    parts = _parts(path)
    if objects_root:
        root = _parts(objects_root)
        lowered = [p.lower() for p in parts]
        if len(parts) > len(root) + 1 and lowered[: len(root)] == [p.lower() for p in root]:
            return parts[len(root)]
    for i, part in enumerate(parts[:-2]):
        if ROOT_MARKER in part.lower():
            return parts[i + 1]
    return None


def parent_folder(path: str | None) -> str | None:
    if not path:
        return None
    parts = _parts(path)
    return parts[-2] if len(parts) >= 2 else None


def split_names(folders: set[str]) -> dict[str, tuple[str, str]]:
    """Maps each project folder name to (object, topic)."""
    words = {f: f.split() for f in folders}
    result = {}
    for folder, w in words.items():
        result[folder] = (folder, "")
        for k in range(len(w) - 1, 0, -1):
            prefix = [x.lower() for x in w[:k]]
            if any(o != folder and [x.lower() for x in ow[:k]] == prefix and len(ow) > k
                   for o, ow in words.items()):
                result[folder] = (" ".join(w[:k]), " ".join(w[k:]))
                break
    return result


def list_project_folders(objects_root: str) -> set[str]:
    if not objects_root or not os.path.isdir(objects_root):
        return set()
    return {e.name for e in os.scandir(objects_root) if e.is_dir()}
