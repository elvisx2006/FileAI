"""Organizer — moves files according to the classification plan."""
from __future__ import annotations

import logging
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from backend.config import get_config
from backend.models import ClassifyResult, OperationRecord, OrganizePlan
from backend.services import icloud

logger = logging.getLogger(__name__)

ProgressCallback = Optional[Callable[[int, int, str], None]]


def _unique_destination(dst_dir: Path, filename: str) -> Path:
    """Pick dst path; if taken, use ``name (2).ext`` style names like Finder."""
    dst = dst_dir / filename
    if not dst.exists():
        return dst
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    n = 2
    while n < 10_000:
        candidate = dst_dir / f"{stem} ({n}){suffix}"
        if not candidate.exists():
            return candidate
        n += 1
    return dst_dir / f"{stem}_{int(time.time())}{suffix}"


def _cleanup_empty_dirs_after_organize(
    moved_sources: list[Path],
    watch_roots: set[Path],
    organize_base: Path,
) -> int:
    """Remove empty parent folders left after moves (never watch roots or organize base)."""
    if not moved_sources:
        return 0
    try:
        ob = organize_base.resolve()
    except OSError:
        ob = organize_base
    roots = set()
    for r in watch_roots:
        try:
            roots.add(r.resolve())
        except OSError:
            roots.add(r)

    candidates: set[Path] = set()
    for sp in moved_sources:
        try:
            p = Path(sp).resolve().parent
        except OSError:
            continue
        while True:
            candidates.add(p)
            if p in roots or p == ob:
                break
            parent = p.parent
            if parent == p:
                break
            p = parent

    removed = 0
    for d in sorted(candidates, key=lambda x: len(x.parts), reverse=True):
        try:
            if not d.is_dir() or d in roots or d == ob:
                continue
            if not any(d.iterdir()):
                d.rmdir()
                removed += 1
        except OSError:
            pass
    return removed


def build_plan(items: list[ClassifyResult], dry_run: bool = True) -> OrganizePlan:
    return OrganizePlan(
        id=str(uuid.uuid4())[:8],
        items=items,
        dry_run=dry_run,
    )


def execute_plan(
    plan: OrganizePlan,
    on_progress: ProgressCallback = None,
) -> dict:
    """Execute a plan. Returns dict with records, errors, skipped counts, empty_dirs_removed."""
    config = get_config()
    base = config.get_organize_base()
    records: list[OperationRecord] = []
    errors: list[dict] = []
    skipped = 0
    total = len(plan.items)

    for idx, item in enumerate(plan.items):
        src = Path(item.original_path)
        move_name = src.stem if src.name.endswith(".icloud") else src.name

        if not src.exists():
            skipped += 1
            if on_progress:
                on_progress(idx + 1, total, move_name)
            continue
        src_local = icloud.ensure_local_file(src) if not plan.dry_run else src.resolve()
        if not plan.dry_run and src_local is None:
            logger.error("Could not materialize iCloud file: %s", src)
            errors.append({
                "file": move_name,
                "source": str(src),
                "dest": "",
                "error": "iCloud 文件无法下载到本地（请检查网络与 iCloud 同步）",
            })
            if on_progress:
                on_progress(idx + 1, total, move_name)
            continue

        if plan.dry_run:
            src_for_record = src.resolve()
        else:
            src_for_record = src_local

        dst_dir = base / item.target_folder
        dst = _unique_destination(dst_dir, move_name)

        if not plan.dry_run:
            try:
                dst_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src_for_record), str(dst))
            except Exception as e:
                logger.error(f"Failed to move {src_for_record} -> {dst}: {e}")
                errors.append({
                    "file": move_name,
                    "source": str(src_for_record),
                    "dest": str(dst),
                    "error": str(e),
                })
                if on_progress:
                    on_progress(idx + 1, total, move_name)
                continue

        record = OperationRecord(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.now().isoformat(),
            source_path=str(src_for_record),
            dest_path=str(dst),
            file_name=move_name,
            operation="move",
        )
        records.append(record)

        if on_progress:
            on_progress(idx + 1, total, move_name)

    moved_sources = [Path(r.source_path) for r in records]
    empty_removed = 0
    if config.scan.cleanup_empty_dirs and not plan.dry_run and moved_sources:
        watch_roots = {p for p in config.get_watch_dirs()}
        empty_removed = _cleanup_empty_dirs_after_organize(moved_sources, watch_roots, base)
        if empty_removed:
            logger.info("Removed %s empty directories after organize", empty_removed)

    return {
        "records": records,
        "errors": errors,
        "skipped": skipped,
        "total": total,
        "empty_dirs_removed": empty_removed,
    }


def undo_operation(record: OperationRecord) -> bool:
    """Move a file back to its original location."""
    dst = Path(record.dest_path)
    src = Path(record.source_path)

    if not dst.exists():
        return False

    src.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(dst), str(src))
    return True
