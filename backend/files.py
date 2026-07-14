from __future__ import annotations

from pathlib import Path
from typing import Any

from config import ROOT_PATH


WEB_WORKSPACE_PATH = ROOT_PATH / "workspace"
WEB_UPLOADS_PATH = WEB_WORKSPACE_PATH / "uploads"
WEB_ANALYSES_PATH = WEB_WORKSPACE_PATH / "analyses"

VIEWABLE_FILE_EXTENSIONS = {
    ".json",
    ".md",
    ".txt",
    ".log",
    ".yaml",
    ".yml",
}
MAX_VIEWABLE_FILE_SIZE = 2 * 1024 * 1024


async def save_upload_file(upload: Any, analysis_id: str) -> tuple[str, Path]:
    filename = safe_filename(upload.filename)

    upload_dir = WEB_UPLOADS_PATH / analysis_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    sample_path = upload_dir / filename
    with sample_path.open("wb") as target:
        while chunk := await upload.read(1024 * 1024):
            target.write(chunk)

    return filename, sample_path


def safe_filename(filename: str | None) -> str:
    if not filename:
        return "sample.bin"

    safe = Path(filename).name.strip()
    return safe or "sample.bin"


def is_viewable_file(path: Path) -> bool:
    size = path.stat().st_size
    return has_viewable_extension(path) and size <= MAX_VIEWABLE_FILE_SIZE


def has_viewable_extension(path: Path) -> bool:
    return path.suffix.lower() in VIEWABLE_FILE_EXTENSIONS


def read_text_prefix(path: Path) -> str:
    with path.open("r", encoding="utf-8", errors="replace") as file:
        return file.read(MAX_VIEWABLE_FILE_SIZE)
