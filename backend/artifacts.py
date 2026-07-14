from __future__ import annotations

import json
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from backend.analysis import AnalysisStore, PHASES
from backend.files import (
    MAX_VIEWABLE_FILE_SIZE,
    WEB_ANALYSES_PATH,
    has_viewable_extension,
    is_viewable_file,
    read_text_prefix,
)
from config import (
    DYNAMIC_INFERENCE_RESULT_FILENAME,
    ENRICHMENT_FILENAME,
    REPORT_FILENAME,
    RESULT_FILENAME,
    REVERSING_AGENT_RESULT_FILENAME,
    STATIC_STRINGS_INFERENCE_RESULT_FILENAME,
)
from core.utils.io.files import load_json
from core.utils.io.text import read_text


ARTIFACT_FILENAMES = (
    RESULT_FILENAME,
    STATIC_STRINGS_INFERENCE_RESULT_FILENAME,
    DYNAMIC_INFERENCE_RESULT_FILENAME,
    ENRICHMENT_FILENAME,
    REVERSING_AGENT_RESULT_FILENAME,
    REPORT_FILENAME,
)


def list_analyses(store: AnalysisStore) -> dict[str, Any]:
    analyses: dict[str, dict[str, Any]] = {}

    if WEB_ANALYSES_PATH.exists():
        for path in sorted(WEB_ANALYSES_PATH.iterdir()):
            if path.is_dir():
                analyses[path.name] = analysis_status(store, path.name)

    analyses.update(store.list_statuses())

    return {
        "available": True,
        "analyses": sorted(
            analyses.values(),
            key=lambda item: str(item.get("created_at") or ""),
            reverse=True,
        ),
    }


def analysis_status(store: AnalysisStore, analysis_id: str) -> dict[str, Any]:
    try:
        return store.status(analysis_id)
    except KeyError:
        status = _disk_analysis_status(analysis_id)
        if status is None:
            raise HTTPException(
                status_code=404, 
                detail="Analysis not found",
            )
        
        return status


def list_analysis_files(store: AnalysisStore, analysis_id: str) -> dict[str, Any]:
    artifact_dir = _artifact_dir(store, analysis_id)
    if artifact_dir is None or not artifact_dir.exists():
        return {"available": False, "files": []}

    files = []
    for path in sorted(artifact_dir.rglob("*")):
        if not path.is_file():
            continue

        relative_path = path.relative_to(artifact_dir).as_posix()
        stat = path.stat()
        files.append(
            {
                "path": relative_path,
                "name": path.name,
                "size": stat.st_size,
                "modified_at": datetime.fromtimestamp(
                    stat.st_mtime,
                    timezone.utc,
                ).isoformat(),
                "content_type": mimetypes.guess_type(path.name)[0],
                "viewable": is_viewable_file(path),
                "endpoint": f"/api/analyses/{analysis_id}/files/{relative_path}",
            }
        )

    return {
        "available": True,
        "root": str(artifact_dir),
        "files": files,
    }


def read_analysis_file(
    store: AnalysisStore,
    analysis_id: str,
    file_path: str,
) -> dict[str, Any]:
    path = _resolve_artifact_file(store, analysis_id, file_path)
    stat = path.stat()
    content_type = mimetypes.guess_type(path.name)[0]

    response: dict[str, Any] = {
        "available": True,
        "path": file_path,
        "name": path.name,
        "size": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "content_type": content_type,
        "viewable": is_viewable_file(path),
        "truncated": False,
        "content": None,
        "data": None,
    }

    if not has_viewable_extension(path):
        return response

    if stat.st_size > MAX_VIEWABLE_FILE_SIZE:
        response["truncated"] = True
        response["content"] = read_text_prefix(path)
        return response

    content = read_text(path)
    if path.suffix.lower() == ".json":
        try:
            response["data"] = json.loads(content)
        except json.JSONDecodeError:
            response["content"] = content
        return response

    response["content"] = content
    return response


def json_artifact(
    store: AnalysisStore,
    analysis_id: str,
    filename: str,
) -> dict[str, Any]:
    artifact_dir = _artifact_dir(store, analysis_id)
    if artifact_dir is None or not (artifact_dir / filename).exists():
        return {"available": False, "data": None}

    return {
        "available": True,
        "data": load_json(artifact_dir, filename),
    }


def text_artifact(
    store: AnalysisStore,
    analysis_id: str,
    filename: str,
) -> dict[str, Any]:
    artifact_dir = _artifact_dir(store, analysis_id)
    if artifact_dir is None:
        return {"available": False, "content": ""}

    path = artifact_dir / filename
    if not path.exists():
        return {"available": False, "content": ""}

    return {
        "available": True,
        "content": read_text(path),
    }


def _artifact_dir(store: AnalysisStore, analysis_id: str) -> Path | None:
    try:
        job = store.get(analysis_id)
    except KeyError:
        return _disk_artifact_dir(analysis_id)

    if job.output_dir is not None:
        return Path(job.output_dir)

    return _disk_artifact_dir(analysis_id)


def _disk_analysis_status(analysis_id: str) -> dict[str, Any] | None:
    analysis_dir = _disk_analysis_dir(analysis_id)
    if analysis_dir is None:
        return None

    artifact_dir = _find_artifact_dir(analysis_dir)
    phases = {phase: "pending" for phase in PHASES}

    analysis_data = load_json(artifact_dir, RESULT_FILENAME) or {}
    analysis_phases = analysis_data.get("phases")
    if isinstance(analysis_phases, dict):
        if analysis_phases.get("static"):
            phases["static"] = "completed"
        if analysis_phases.get("dynamic"):
            phases["dynamic"] = "completed"
        if analysis_phases.get("reversing"):
            phases["reverse_info"] = "completed"

    if (artifact_dir / STATIC_STRINGS_INFERENCE_RESULT_FILENAME).exists():
        phases["static_inference"] = "completed"
    if (artifact_dir / DYNAMIC_INFERENCE_RESULT_FILENAME).exists():
        phases["dynamic_inference"] = "completed"
    if (artifact_dir / ENRICHMENT_FILENAME).exists():
        phases["enrichment"] = "completed"
    if (artifact_dir / REVERSING_AGENT_RESULT_FILENAME).exists():
        phases["reverse_agent"] = "completed"
    if (artifact_dir / REPORT_FILENAME).exists():
        phases["report"] = "completed"

    sample = analysis_data.get("sample")
    sample_path = sample.get("path") if isinstance(sample, dict) else None
    sample_sha256 = sample.get("sha256") if isinstance(sample, dict) else None
    created_at = datetime.fromtimestamp(
        analysis_dir.stat().st_mtime,
        timezone.utc,
    ).isoformat()

    return {
        "analysis_id": analysis_id,
        "status": "completed",
        "current_phase": None,
        "phases": phases,
        "error": None,
        "filename": Path(sample_path).name if isinstance(sample_path, str) else analysis_id,
        "sample_sha256": sample_sha256 if isinstance(sample_sha256, str) else artifact_dir.name,
        "output_dir": str(artifact_dir),
        "created_at": created_at,
    }


def _disk_analysis_dir(analysis_id: str) -> Path | None:
    root = WEB_ANALYSES_PATH.resolve()
    candidate = (WEB_ANALYSES_PATH / analysis_id).resolve()

    if candidate != root and root not in candidate.parents:
        raise HTTPException(status_code=400, detail="Invalid analysis id")
    if not candidate.exists() or not candidate.is_dir():
        return None

    return candidate


def _disk_artifact_dir(analysis_id: str) -> Path | None:
    analysis_dir = _disk_analysis_dir(analysis_id)
    if analysis_dir is None:
        return None

    return _find_artifact_dir(analysis_dir)


def _find_artifact_dir(analysis_dir: Path) -> Path:
    if _has_known_artifact(analysis_dir):
        return analysis_dir

    candidates = [
        path
        for path in analysis_dir.iterdir()
        if path.is_dir() and _has_known_artifact(path)
    ]
    if candidates:
        return max(candidates, key=lambda path: path.stat().st_mtime)

    child_dirs = [path for path in analysis_dir.iterdir() if path.is_dir()]
    if len(child_dirs) == 1:
        return child_dirs[0]

    return analysis_dir


def _has_known_artifact(path: Path) -> bool:
    return any((path / filename).exists() for filename in ARTIFACT_FILENAMES)


def _resolve_artifact_file(
    store: AnalysisStore,
    analysis_id: str,
    file_path: str,
) -> Path:
    artifact_dir = _artifact_dir(store, analysis_id)
    if artifact_dir is None or not artifact_dir.exists():
        raise HTTPException(status_code=404, detail="Analysis files not available")

    root = artifact_dir.resolve()
    target = (artifact_dir / file_path).resolve()
    if target != root and root not in target.parents:
        raise HTTPException(status_code=400, detail="Invalid file path")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Analysis file not found")

    return target
