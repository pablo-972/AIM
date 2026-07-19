import json
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from backend.storage import is_viewable_file


def _resolve_artifact_file(
    artifact_dir: Path | None,
    file_path: str,
) -> Path:
    if artifact_dir is None or not artifact_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="Analysis files not available",
        )

    root = artifact_dir.resolve()
    target = (artifact_dir / file_path).resolve()

    if not _is_path_inside(root, target):
        raise HTTPException(
            status_code=400,
            detail="Invalid file path",
        )

    if not target.exists() or not target.is_file():
        raise HTTPException(
            status_code=404,
            detail="Analysis file not found",
        )

    return target


def _is_path_inside(
    root: Path,
    candidate: Path,
) -> bool:
    if candidate == root:
        return True

    return root in candidate.parents


def _create_file_status(
    path: Path,
    artifact_dir: Path,
    analysis_id: str,
) -> dict[str, Any]:
    relative_path = path.relative_to(artifact_dir).as_posix()
    stat = path.stat()
    modified_at = _format_modified_at(stat.st_mtime)
    content_type = mimetypes.guess_type(path.name)[0]
    viewable = is_viewable_file(path)
    endpoint = f"/api/analyses/{analysis_id}/files/{relative_path}"

    return {
        "path": relative_path,
        "name": path.name,
        "size": stat.st_size,
        "modified_at": modified_at,
        "content_type": content_type,
        "viewable": viewable,
        "endpoint": endpoint,
    }


def _create_file_response(
    path: Path,
    file_path: str,
) -> dict[str, Any]:
    stat = path.stat()
    content_type = mimetypes.guess_type(path.name)[0]
    modified_at = _format_modified_at(stat.st_mtime)

    return {
        "available": True,
        "path": file_path,
        "name": path.name,
        "size": stat.st_size,
        "modified_at": modified_at,
        "content_type": content_type,
        "viewable": is_viewable_file(path),
        "truncated": False,
        "content": None,
        "data": None,
    }


def _set_json_content(
    response: dict[str, Any],
    content: str,
) -> None:
    try:
        response["data"] = json.loads(content)
    except json.JSONDecodeError:
        response["content"] = content


def _format_modified_at(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def _analysis_created_at(analysis: dict[str, Any]) -> str:
    created_at = analysis.get("created_at")
    if isinstance(created_at, str):
        return created_at

    return ""
