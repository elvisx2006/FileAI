from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    path: str
    name: str
    extension: str
    size: int
    modified_time: float
    modified_date: str
    parent_dir: str
    id: str = ""
    # "local" | "icloud_placeholder" — placeholder is a *.icloud stub before download
    storage_state: str = "local"

    def model_post_init(self, __context):
        if not self.id:
            self.id = str(hash(self.path))


class ClassifyResult(BaseModel):
    original_path: str
    target_folder: str
    confidence: float = 1.0
    reason: str = ""
    source: str = "rule"  # "rule" or "ai"


class OrganizePlan(BaseModel):
    id: str = ""
    items: list[ClassifyResult] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    dry_run: bool = True


class OperationRecord(BaseModel):
    id: str
    timestamp: str
    source_path: str
    dest_path: str
    file_name: str
    operation: str = "move"
    undone: bool = False


class OperationStatus(str, Enum):
    PENDING = "pending"
    PREVIEW = "preview"
    CONFIRMED = "confirmed"
    DONE = "done"
    UNDONE = "undone"


class ScanResult(BaseModel):
    directory: str
    files: list[FileInfo]
    total_count: int
    total_size: int


class StatsData(BaseModel):
    total_files_organized: int = 0
    total_operations: int = 0
    watch_dirs_status: dict = Field(default_factory=dict)
    recent_operations: list[OperationRecord] = Field(default_factory=list)
    category_distribution: dict = Field(default_factory=dict)
