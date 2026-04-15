"""History — SQLite-backed operation log with undo support."""
from __future__ import annotations

import aiosqlite
import os
from pathlib import Path
from typing import Optional

from backend.models import OperationRecord

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db", "history.db")

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS operations (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    source_path TEXT NOT NULL,
    dest_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    operation TEXT NOT NULL DEFAULT 'move',
    undone INTEGER NOT NULL DEFAULT 0
);
"""


async def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(_CREATE_TABLE)
        await db.commit()


async def save_records(records: list[OperationRecord]):
    async with aiosqlite.connect(DB_PATH) as db:
        for r in records:
            await db.execute(
                "INSERT OR REPLACE INTO operations (id, timestamp, source_path, dest_path, file_name, operation, undone) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (r.id, r.timestamp, r.source_path, r.dest_path, r.file_name, r.operation, int(r.undone)),
            )
        await db.commit()


async def mark_undone(operation_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE operations SET undone = 1 WHERE id = ?", (operation_id,))
        await db.commit()


async def get_history(page: int = 1, page_size: int = 50) -> list[OperationRecord]:
    offset = (page - 1) * page_size
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM operations ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (page_size, offset),
        )
        rows = await cursor.fetchall()
        return [
            OperationRecord(
                id=row["id"],
                timestamp=row["timestamp"],
                source_path=row["source_path"],
                dest_path=row["dest_path"],
                file_name=row["file_name"],
                operation=row["operation"],
                undone=bool(row["undone"]),
            )
            for row in rows
        ]


async def get_record(operation_id: str) -> Optional[OperationRecord]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM operations WHERE id = ?", (operation_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return OperationRecord(
            id=row["id"],
            timestamp=row["timestamp"],
            source_path=row["source_path"],
            dest_path=row["dest_path"],
            file_name=row["file_name"],
            operation=row["operation"],
            undone=bool(row["undone"]),
        )


async def get_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM operations WHERE undone = 0")
        total = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT dest_path FROM operations WHERE undone = 0 ORDER BY timestamp DESC LIMIT 200"
        )
        rows = await cursor.fetchall()

        category_counts: dict[str, int] = {}
        for (dest_path,) in rows:
            parts = dest_path.split("/")
            organized_idx = None
            for i, p in enumerate(parts):
                if p == "Organized":
                    organized_idx = i
                    break
            if organized_idx is not None and organized_idx + 1 < len(parts):
                category = parts[organized_idx + 1]
                category_counts[category] = category_counts.get(category, 0) + 1

        return {
            "total_operations": total,
            "category_distribution": category_counts,
        }
