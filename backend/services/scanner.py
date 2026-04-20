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


def _path_under_organize_base(path: Path, organize_base: Path) -> bool:
    try:
        path.resolve().relative_to(organize_base.expanduser().resolve())
        return True
    except ValueError:
        return False


def _dir_has_project_marker(dir_path: Path, markers: frozenset[str]) -> bool:
    try:
        for name in os.listdir(dir_path):
            if name in markers:
                return True
    except OSError:
        return False
    return False


def _bundle_total_size(path: Path) -> int:
    total = 0
    try:
        for p in path.rglob("*"):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def _append_file_info(results: list[FileInfo], total_size: list[int], fpath: Path, config) -> None:
    """Mutate results and total_size[0]."""
    fname = fpath.name
    if fname.startswith(".") or _should_exclude(fpath, fname, config):
        return
    if fname.endswith(".icloud"):
        real_candidate = fpath.parent / Path(fname).stem
        if real_candidate.exists() and real_candidate.is_file():
            return
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
        total_size[0] += stat.st_size
    except (PermissionError, OSError):
        pass


def _append_bundle_info(
    results: list[FileInfo],
    total_size: list[int],
    bundle_path: Path,
    config,
) -> None:
    try:
        stat = bundle_path.stat()
        mod_dt = datetime.fromtimestamp(stat.st_mtime)
        sz = _bundle_total_size(bundle_path)
        info = FileInfo(
            path=str(bundle_path),
            name=bundle_path.name,
            extension=bundle_path.suffix.lower(),
            size=sz,
            modified_time=stat.st_mtime,
            modified_date=mod_dt.strftime("%Y-%m"),
            parent_dir=str(bundle_path.parent),
            storage_state="local",
        )
        results.append(info)
        total_size[0] += sz
    except (PermissionError, OSError):
        pass


def scan_directory(target_dir: str) -> ScanResult:
    config = get_config()
    root = Path(target_dir).expanduser()
    if not root.exists():
        return ScanResult(directory=str(root), files=[], total_count=0, total_size=0)

    organize_base = config.get_organize_base()
    max_depth = config.scan.max_depth
    marker_set = frozenset(config.scan.project_markers)
    bundle_suffixes = tuple(s.lower() for s in config.scan.bundle_suffixes)

    def is_bundle_name(name: str) -> bool:
        lower = name.lower()
        return any(lower.endswith(suf) for suf in bundle_suffixes)

    results: list[FileInfo] = []
    total_size = [0]
    root_res = root.resolve()

    for dirpath, dirnames, filenames in os.walk(root_res, topdown=True):
        dir_path = Path(dirpath)

        try:
            rel = dir_path.resolve().relative_to(root_res)
        except ValueError:
            rel = Path()
        rel_depth = len(rel.parts)

        if _path_under_organize_base(dir_path, organize_base):
            dirnames[:] = []
            continue

        if config.scan.skip_project_dirs and _dir_has_project_marker(dir_path, marker_set):
            dirnames[:] = []
            continue

        raw_dirs = list(dirnames)
        dirnames.clear()
        for d in raw_dirs:
            if d in config.safety.exclude_dirs or d.startswith("."):
                continue
            if is_bundle_name(d):
                _append_bundle_info(results, total_size, dir_path / d, config)
                continue
            dirnames.append(d)

        if max_depth >= 0 and rel_depth >= max_depth:
            dirnames.clear()

        dirnames[:] = [
            d for d in dirnames
            if d not in config.safety.exclude_dirs and not d.startswith(".")
        ]

        for fname in filenames:
            fpath = dir_path / fname
            _append_file_info(results, total_size, fpath, config)

    return ScanResult(
        directory=str(root),
        files=results,
        total_count=len(results),
        total_size=total_size[0],
    )


def scan_all_watched() -> list[ScanResult]:
    config = get_config()
    results = []
    for d in config.get_watch_dirs():
        results.append(scan_directory(str(d)))
    return results
