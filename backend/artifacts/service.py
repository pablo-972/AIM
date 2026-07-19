from pathlib import Path
from typing import Any

from fastapi import HTTPException

from core.utils.io.files import load_json
from core.utils.io.text import read_text
from backend.artifacts.disk import (
    disk_analysis_status,
    disk_artifact_dir,
    disk_status_by_sha256,
)
from backend.artifacts.files import (
    analysis_created_at,
    create_file_response,
    create_file_status,
    resolve_artifact_file,
    set_json_content,
)
from backend.analysis.service import AnalysisService
from backend.storage import (
    MAX_VIEWABLE_FILE_SIZE,
    WEB_ANALYSES_PATH,
    has_viewable_extension,
    read_text_prefix,
)


def list_analyses(store: AnalysisService) -> dict[str, Any]:
    analyses: dict[str, dict[str, Any]] = {}

    if WEB_ANALYSES_PATH.exists():
        web_analyses_iter = sorted(WEB_ANALYSES_PATH.iterdir())
        for path in web_analyses_iter:
            if not path.is_dir():
                continue

            status = disk_analysis_status(path.name)
            if status is None:
                continue

            analyses[path.name] = status

    analyses.update(store.list_statuses())

    analysis_list = list(analyses.values())
    analysis_list.sort(key=analysis_created_at, reverse=True)

    return {
        "available": True,
        "analyses": analysis_list,
    }


def resolve_analysis(store: AnalysisService, identifier: str) -> dict[str, Any]:
    status = _find_analysis_status(store, identifier)
    if status is not None:
        return status

    raise HTTPException(
        status_code=404,
        detail="Analysis not found",
    )


def analysis_status(store: AnalysisService, analysis_id: str) -> dict[str, Any]:
    status = _find_analysis_status(store, analysis_id)
    if status is not None:
        return status

    raise HTTPException(
        status_code=404,
        detail="Analysis not found",
    )


def json_artifact(
    store: AnalysisService,
    analysis_id: str,
    filename: str,
) -> dict[str, Any]:
    artifact_dir = _artifact_dir(store, analysis_id)
    if artifact_dir is None:
        return {
            "available": False,
            "data": None,
        }

    path = artifact_dir / filename
    if not path.exists():
        return {
            "available": False,
            "data": None,
        }

    return {
        "available": True,
        "data": load_json(artifact_dir, filename),
    }


def text_artifact(
    store: AnalysisService,
    analysis_id: str,
    filename: str,
) -> dict[str, Any]:
    artifact_dir = _artifact_dir(store, analysis_id)
    if artifact_dir is None:
        return {
            "available": False,
            "content": "",
        }

    path = artifact_dir / filename
    if not path.exists():
        return {
            "available": False,
            "content": "",
        }

    return {
        "available": True,
        "content": read_text(path),
    }


def list_analysis_files(store: AnalysisService, analysis_id: str) -> dict[str, Any]:
    artifact_dir = _artifact_dir(store, analysis_id)
    if artifact_dir is None or not artifact_dir.exists():
        return {
            "available": False,
            "files": [],
        }

    files = []
    for path in sorted(artifact_dir.rglob("*")):
        if not path.is_file():
            continue

        file_status = create_file_status(path, artifact_dir, analysis_id)
        files.append(file_status)

    return {
        "available": True,
        "root": str(artifact_dir),
        "files": files,
    }


def read_analysis_file(
    store: AnalysisService,
    analysis_id: str,
    file_path: str,
) -> dict[str, Any]:
    artifact_dir = _artifact_dir(store, analysis_id)
    path = resolve_artifact_file(artifact_dir, file_path)
    response = create_file_response(path, file_path)

    if not has_viewable_extension(path):
        return response

    if response["size"] > MAX_VIEWABLE_FILE_SIZE:
        response["truncated"] = True
        response["content"] = read_text_prefix(path)
        return response

    content = read_text(path)
    if path.suffix.lower() == ".json":
        set_json_content(response, content)
        return response

    response["content"] = content
    return response


def _find_analysis_status(
    store: AnalysisService,
    identifier: str,
) -> dict[str, Any] | None:
    status = _memory_status_by_id(store, identifier)
    if status is not None:
        return status

    status = disk_analysis_status(identifier)
    if status is not None:
        return status

    status = _memory_status_by_sha256(store, identifier)
    if status is not None:
        return status

    return disk_status_by_sha256(identifier)


def _memory_status_by_id(
    store: AnalysisService,
    analysis_id: str,
) -> dict[str, Any] | None:
    try:
        return store.status(analysis_id)
    except KeyError:
        return None


def _memory_status_by_sha256(
    store: AnalysisService,
    sample_sha256: str,
) -> dict[str, Any] | None:
    for status in store.list_statuses().values():
        if status.get("sample_sha256") == sample_sha256:
            return status

    return None


def _memory_job(store: AnalysisService, analysis_id: str) -> Any | None:
    try:
        return store.get(analysis_id)
    except KeyError:
        return None


def _artifact_dir(store: AnalysisService, analysis_id: str) -> Path | None:
    job = _memory_job(store, analysis_id)
    if job is not None:
        if job.output_dir is not None:
            return Path(job.output_dir)

        return disk_artifact_dir(analysis_id)

    disk_dir = disk_artifact_dir(analysis_id)
    if disk_dir is not None:
        return disk_dir

    return _artifact_dir_by_sha256(store, analysis_id)


def _artifact_dir_by_sha256(
    store: AnalysisService,
    sample_sha256: str,
) -> Path | None:
    status = _memory_status_by_sha256(store, sample_sha256)
    if status is not None and isinstance(status.get("output_dir"), str):
        return Path(status["output_dir"])

    status = disk_status_by_sha256(sample_sha256)
    if status is not None and isinstance(status.get("output_dir"), str):
        return Path(status["output_dir"])

    return None
