"""Rule engine — fast pattern-based classification without AI calls."""
from __future__ import annotations

import fnmatch
from pathlib import Path

from backend.models import ClassifyResult, FileInfo

EXTENSION_RULES: dict[str, str] = {
    # Documents
    ".pdf": "Documents/PDF",
    ".doc": "Documents/Word",
    ".docx": "Documents/Word",
    ".xls": "Documents/Spreadsheets",
    ".xlsx": "Documents/Spreadsheets",
    ".ppt": "Documents/Presentations",
    ".pptx": "Documents/Presentations",
    ".txt": "Documents/Text",
    ".rtf": "Documents/Text",
    ".pages": "Documents/Pages",
    ".numbers": "Documents/Spreadsheets",
    ".keynote": "Documents/Presentations",
    ".md": "Documents/Markdown",

    # Images
    ".jpg": "Images/Photos",
    ".jpeg": "Images/Photos",
    ".png": "Images/Photos",
    ".gif": "Images/Photos",
    ".webp": "Images/Photos",
    ".svg": "Images/Design/Icons",
    ".ico": "Images/Design/Icons",
    ".bmp": "Images/Photos",
    ".tiff": "Images/Photos",
    ".heic": "Images/Photos",
    ".raw": "Images/Photos",

    # Videos
    ".mp4": "Videos",
    ".mov": "Videos",
    ".avi": "Videos",
    ".mkv": "Videos",
    ".wmv": "Videos",
    ".flv": "Videos",
    ".webm": "Videos",

    # Audio
    ".mp3": "Audio/Music",
    ".wav": "Audio",
    ".flac": "Audio/Music",
    ".aac": "Audio/Music",
    ".ogg": "Audio/Music",
    ".m4a": "Audio",
    ".wma": "Audio/Music",

    # Code
    ".py": "Code/Scripts",
    ".js": "Code/Scripts",
    ".ts": "Code/Scripts",
    ".jsx": "Code/Scripts",
    ".tsx": "Code/Scripts",
    ".java": "Code/Projects",
    ".cpp": "Code/Projects",
    ".c": "Code/Projects",
    ".h": "Code/Projects",
    ".go": "Code/Projects",
    ".rs": "Code/Projects",
    ".swift": "Code/Projects",
    ".rb": "Code/Scripts",
    ".php": "Code/Scripts",
    ".sh": "Code/Scripts",
    ".bash": "Code/Scripts",
    ".sql": "Code/Data/SQL",
    ".json": "Code/Data/JSON",
    ".xml": "Code/Configs",
    ".yaml": "Code/Configs",
    ".yml": "Code/Configs",
    ".toml": "Code/Configs",
    ".ini": "Code/Configs",
    ".env": "Code/Configs",
    ".csv": "Code/Data/CSV",
    ".ipynb": "Code/Scripts",

    # Archives
    ".zip": "Archives/Compressed",
    ".rar": "Archives/Compressed",
    ".7z": "Archives/Compressed",
    ".tar": "Archives/Compressed",
    ".gz": "Archives/Compressed",
    ".bz2": "Archives/Compressed",
    ".xz": "Archives/Compressed",
    ".dmg": "Installers",
    ".pkg": "Installers",
    ".iso": "Archives/Disk_Images",

    # Design
    ".psd": "Design/PSD",
    ".ai": "Design/AI_Illustrator",
    ".sketch": "Design/Sketch",
    ".fig": "Design/Figma",
    ".xd": "Design/XD",

    # Ebooks
    ".epub": "Documents/Study/Ebooks",
    ".mobi": "Documents/Study/Ebooks",

    # Fonts
    ".ttf": "Design/Fonts",
    ".otf": "Design/Fonts",
    ".woff": "Design/Fonts",
    ".woff2": "Design/Fonts",
}

NAME_PATTERNS: list[tuple[str, str, float]] = [
    # (filename_pattern, target_folder, confidence)
    ("Screenshot*", "Images/Screenshots", 0.98),
    ("截屏*", "Images/Screenshots", 0.98),
    ("Screen Recording*", "Videos/Recordings", 0.98),
    ("屏幕录制*", "Videos/Recordings", 0.98),
    ("IMG_*", "Images/Photos", 0.90),
    ("DSC_*", "Images/Photos", 0.90),
    ("DCIM*", "Images/Photos", 0.90),
    ("*resume*", "Documents/Personal/Resumes", 0.85),
    ("*简历*", "Documents/Personal/Resumes", 0.85),
    ("*invoice*", "Documents/Personal/Finance", 0.85),
    ("*发票*", "Documents/Personal/Finance", 0.85),
    ("*report*", "Documents/Work/Reports", 0.80),
    ("*报告*", "Documents/Work/Reports", 0.80),
    ("*contract*", "Documents/Work/Contracts", 0.80),
    ("*合同*", "Documents/Work/Contracts", 0.80),
    ("*wallpaper*", "Images/Wallpapers", 0.85),
    ("*壁纸*", "Images/Wallpapers", 0.85),
]


def classify_by_rules(file: FileInfo) -> ClassifyResult | None:
    name_lower = file.name.lower()

    # Priority 1: filename patterns (more specific)
    for pattern, target, conf in NAME_PATTERNS:
        if fnmatch.fnmatch(name_lower, pattern.lower()):
            final_target = target
            if target in ("Images/Screenshots", "Images/Photos"):
                final_target = f"{target}/{file.modified_date}"
            return ClassifyResult(
                original_path=file.path,
                target_folder=final_target,
                confidence=conf,
                reason=f"Filename matches pattern '{pattern}'",
                source="rule",
            )

    # Priority 2: extension-based rules
    if file.extension in EXTENSION_RULES:
        target = EXTENSION_RULES[file.extension]
        if target.startswith("Images/Photos"):
            target = f"{target}/{file.modified_date}"
        return ClassifyResult(
            original_path=file.path,
            target_folder=target,
            confidence=0.85,
            reason=f"Extension '{file.extension}' mapped to '{target}'",
            source="rule",
        )

    return None


def classify_batch_by_rules(files: list[FileInfo]) -> tuple[list[ClassifyResult], list[FileInfo]]:
    """Returns (classified, needs_ai) — classified files and those needing AI."""
    classified = []
    needs_ai = []
    for f in files:
        result = classify_by_rules(f)
        if result:
            classified.append(result)
        else:
            needs_ai.append(f)
    return classified, needs_ai
