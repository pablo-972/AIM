from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

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


async def save_upload_file(upload: Any) -> tuple[str, Path]:
    filename = safe_filename(upload.filename)

    upload_dir = WEB_UPLOADS_PATH / ".tmp" / uuid4().hex
    upload_dir.mkdir(parents=True, exist_ok=True)

    sample_path = upload_dir / filename
    with sample_path.open("wb") as target:
        while chunk := await upload.read(1024 * 1024):
            target.write(chunk)

    return filename, sample_path


def sample_path_for_status(
    status: dict[str, Any],
    analysis_data: dict[str, Any] | None = None,
) -> Path:
    sample_sha256 = status.get("sample_sha256")
    if isinstance(sample_sha256, str):
        canonical_path = WEB_UPLOADS_PATH / sample_sha256
        if canonical_path.exists() and canonical_path.is_file():
            return canonical_path

    if isinstance(analysis_data, dict):
        sample = analysis_data.get("sample")
        if isinstance(sample, dict):
            sample_path = sample.get("path")
            if isinstance(sample_path, str):
                path = Path(sample_path)
                if path.exists() and path.is_file():
                    return path

    raise HTTPException(
        status_code=404,
        detail="Original sample file not available",
    )


def move_upload_to_sample_path(path: Path, sample_sha256: str) -> Path:
    WEB_UPLOADS_PATH.mkdir(parents=True, exist_ok=True)

    target = WEB_UPLOADS_PATH / sample_sha256
    if target.exists():
        if target.is_dir():
            raise HTTPException(
                status_code=409,
                detail="Sample upload path is a directory",
            )

        target.unlink()

    path.replace(target)
    cleanup_empty_dir(path.parent)

    return target


def store_or_discard_duplicate_upload(
    path: Path,
    sample_sha256: str,
) -> None:
    target = WEB_UPLOADS_PATH / sample_sha256
    if target.exists():
        cleanup_upload_temp(path)
        return

    move_upload_to_sample_path(path, sample_sha256)


def cleanup_upload_temp(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return

    cleanup_empty_dir(path.parent)


def cleanup_empty_dir(path: Path) -> None:
    try:
        path.rmdir()
    except OSError:
        return


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
