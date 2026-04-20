"""File scanner — walks target directories and extracts file metadata."""
from __future__ import annotations

import fnmatch
import os
from datetime import datetime
from pathlib import Path

from backend.config import get_config
from backend.models import FileInfo, ScanResult


def _should_exclude(file_path: Path, name: str, config) -> bool:
    for pattern in config.safety.exclude_patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
    parts = file_path.parts
    for d in config.safety.exclude_dirs:
        if d in parts:
            return True
    return False


def scan_directory(target_dir: str, recursive: bool = True) -> ScanResult:
    config = get_config()
    root = Path(target_dir).expanduser()
    if not root.exists():
        return ScanResult(directory=str(root), files=[], total_count=0, total_size=0)

    results: list[FileInfo] = []
    total_size = 0

    if recursive:
        walker = os.walk(root)
    else:
        walker = [(str(root), [d for d in os.listdir(root) if (root / d).is_dir()],
                    [f for f in os.listdir(root) if (root / f).is_file()])]

    for dirpath, dirnames, filenames in (os.walk(root) if recursive else walker):
        dir_path = Path(dirpath)

        dirnames[:] = [
            d for d in dirnames
            if d not in config.safety.exclude_dirs and not d.startswith(".")
        ]

        for fname in filenames:
            fpath = dir_path / fname
            if fname.startswith(".") or _should_exclude(fpath, fname, config):
                continue
            if fname.endswith(".icloud"):
                real_candidate = dir_path / Path(fname).stem
                if real_candidate.exists() and real_candidate.is_file():
                    continue
            try:
                stat = fpath.stat()
                mod_dt = datetime.fromtimestamp(stat.st_mtime)
                if fname.endswith(".icloud"):
                    display_name = fpath.stem
                    ext = Path(display_name).suffix.lower()
                    storage_state = "icloud_placeholder"
                else:
                    display_name = fname
                    ext = fpath.suffix.lower()
                    storage_state = "local"
                info = FileInfo(
                    path=str(fpath),
                    name=display_name,
                    extension=ext,
                    size=stat.st_size,
                    modified_time=stat.st_mtime,
                    modified_date=mod_dt.strftime("%Y-%m"),
                    parent_dir=str(fpath.parent),
                    storage_state=storage_state,
                )
                results.append(info)
                total_size += stat.st_size
            except (PermissionError, OSError):
                continue

    return ScanResult(
        directory=str(root),
        files=results,
        total_count=len(results),
        total_size=total_size,
    )


def scan_all_watched() -> list[ScanResult]:
    config = get_config()
    results = []
    for d in config.get_watch_dirs():
        results.append(scan_directory(str(d), recursive=False))
    return results
