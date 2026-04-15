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

logger = logging.getLogger(__name__)

ProgressCallback = Optional[Callable[[int, int, str], None]]


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
    """Execute a plan. Returns dict with records, errors, and skipped counts."""
    config = get_config()
    base = config.get_organize_base()
    records: list[OperationRecord] = []
    errors: list[dict] = []
    skipped = 0
    total = len(plan.items)

    for idx, item in enumerate(plan.items):
        src = Path(item.original_path)

        if not src.exists():
            skipped += 1
            if on_progress:
                on_progress(idx + 1, total, src.name)
            continue

        dst_dir = base / item.target_folder
        dst = dst_dir / src.name

        if dst.exists():
            stem = dst.stem
            suffix = dst.suffix
            dst = dst_dir / f"{stem}_{int(time.time())}{suffix}"

        if not plan.dry_run:
            try:
                dst_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
            except Exception as e:
                logger.error(f"Failed to move {src} -> {dst}: {e}")
                errors.append({
                    "file": src.name,
                    "source": str(src),
                    "dest": str(dst),
                    "error": str(e),
                })
                if on_progress:
                    on_progress(idx + 1, total, src.name)
                continue

        record = OperationRecord(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.now().isoformat(),
            source_path=str(src),
            dest_path=str(dst),
            file_name=src.name,
            operation="move",
        )
        records.append(record)

        if on_progress:
            on_progress(idx + 1, total, src.name)

    return {
        "records": records,
        "errors": errors,
        "skipped": skipped,
        "total": total,
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
