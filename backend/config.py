from __future__ import annotations
import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field

_DEFAULT_PROJECT_MARKERS = frozenset({
    ".git", ".hg", ".svn",
    "package.json", "pnpm-lock.yaml", "yarn.lock", "package-lock.json",
    "pyproject.toml", "requirements.txt", "Pipfile", "Pipfile.lock",
    "Cargo.toml", "Cargo.lock", "go.mod", "go.sum",
    "pom.xml", "build.gradle", "build.gradle.kts",
})

_DEFAULT_BUNDLE_SUFFIXES = (
    ".app", ".framework", ".bundle", ".photoslibrary", ".imovielibrary",
    ".xcodeproj", ".xcworkspace",
)


class AIConfig(BaseModel):
    provider: str = "deepseek"
    model: str = "deepseek-chat"
    fallback_model: str = "deepseek-chat"
    batch_size: int = 20
    low_confidence_threshold: float = 0.7
    base_url: str = ""


class SafetyConfig(BaseModel):
    dry_run: bool = True
    confirm_before_move: bool = True
    exclude_patterns: list[str] = Field(default_factory=lambda: ["*.app", ".DS_Store"])
    exclude_dirs: list[str] = Field(default_factory=lambda: [".Trash", ".git", "node_modules"])


class ScanConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    #: -1 = unlimited recursion; 0 = watch root only; 1 = one level of subfolders; etc.
    max_depth: int = -1
    skip_project_dirs: bool = True
    cleanup_empty_dirs: bool = True
    project_markers: list[str] = Field(
        default_factory=lambda: sorted(_DEFAULT_PROJECT_MARKERS),
    )
    bundle_suffixes: list[str] = Field(
        default_factory=lambda: list(_DEFAULT_BUNDLE_SUFFIXES),
    )


class AppConfig(BaseModel):
    watch_directories: list[str] = Field(default_factory=lambda: ["~/Downloads", "~/Desktop", "~/Documents"])
    organize_base: str = "~/Organized"
    ai: AIConfig = Field(default_factory=AIConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    scan: ScanConfig = Field(default_factory=ScanConfig)
    category_tree: dict = Field(default_factory=dict)

    def get_watch_dirs(self) -> list[Path]:
        return [Path(d).expanduser() for d in self.watch_directories]

    def get_organize_base(self) -> Path:
        return Path(self.organize_base).expanduser()


_config: Optional[AppConfig] = None


def load_config(path: str | None = None, *, force: bool = False) -> AppConfig:
    global _config
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "config.yaml")
    if _config is not None and not force:
        return _config

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        _config = AppConfig(**data)
    else:
        _config = AppConfig()

    return _config


def save_app_config(
    *,
    watch_directories: list[str] | None = None,
    organize_base: str | None = None,
    scan: dict | None = None,
) -> AppConfig:
    """Merge updates into current config, write backend/config.yaml, refresh cache."""
    global _config
    path = os.path.join(os.path.dirname(__file__), "config.yaml")
    data = get_config().model_dump()
    if watch_directories is not None:
        data["watch_directories"] = watch_directories
    if organize_base is not None:
        data["organize_base"] = organize_base
    if scan is not None:
        cur = dict(data.get("scan") or {})
        for k, v in scan.items():
            if k in ScanConfig.model_fields and v is not None:
                cur[k] = v
        data["scan"] = ScanConfig(**cur).model_dump()
    _config = AppConfig(**data)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            _config.model_dump(),
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )
    return _config


def get_config() -> AppConfig:
    if _config is None:
        return load_config()
    return _config
