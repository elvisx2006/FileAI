"""iCloud Drive helpers — detect placeholders and materialize before local moves (macOS)."""
from __future__ import annotations

import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Standard iCloud Drive folder on macOS (user-visible "iCloud Drive" root).
ICLOUD_DRIVE_REL = Path("Library/Mobile Documents/com~apple~CloudDocs")


def icloud_drive_root() -> Path:
    return Path.home() / ICLOUD_DRIVE_REL


def is_icloud_path(path: Path) -> bool:
    try:
        resolved = path.expanduser().resolve()
        root = icloud_drive_root()
        if not root.exists():
            return False
        resolved.relative_to(root)
        return True
    except ValueError:
        return False
    except (OSError, RuntimeError):
        return False


def is_placeholder_file(path: Path) -> bool:
    return path.is_file() and path.name.endswith(".icloud")


def materialize_placeholder(path: Path, timeout: float = 180.0) -> Optional[Path]:
    """
    Download an iCloud placeholder (.icloud) so the real file exists locally.
    Returns the Path to use for shutil.move, or None on failure.
    """
    path = path.expanduser()
    if not path.exists():
        return None
    if not path.name.endswith(".icloud"):
        return path.resolve()

    real = path.parent / path.stem
    if real.exists() and real.is_file():
        return real.resolve()

    if sys.platform != "darwin":
        logger.warning("iCloud materialize is only supported on macOS; %s", path)
        return real if real.exists() and real.is_file() else None

    try:
        subprocess.run(
            ["brctl", "download", str(path)],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
    except FileNotFoundError:
        logger.warning("brctl not found; cannot materialize %s", path)
    except subprocess.TimeoutExpired:
        logger.warning("brctl download timed out for %s", path)

    deadline = time.time() + timeout
    while time.time() < deadline:
        if real.exists() and real.is_file():
            return real.resolve()
        time.sleep(0.35)

    logger.error("materialize failed (timeout): %s", path)
    return None


def ensure_local_file(path: Path) -> Optional[Path]:
    """
    If path is an iCloud .icloud placeholder, wait for download and return the real file path.
    Otherwise return resolved path if it exists as a file.
    """
    path = path.expanduser()
    if not path.exists():
        return None
    if not path.is_file():
        return None
    if is_placeholder_file(path):
        return materialize_placeholder(path)
    return path.resolve()
