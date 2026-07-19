from pathlib import Path
from typing import Any

from fastapi import HTTPException

from config import (
    DYNAMIC_INFERENCE_RESULT_FILENAME,
    ENRICHMENT_FILENAME,
    REPORT_FILENAME,
    RESULT_FILENAME,
    REVERSING_AGENT_RESULT_FILENAME,
    STATIC_STRINGS_INFERENCE_RESULT_FILENAME,
)
from core.utils.io.files import load_json
from backend.artifacts.files import format_modified_at, is_path_inside
from backend.analysis.models import PHASES
from backend.analysis.status import PhaseStatus
from backend.storage import WEB_ANALYSES_PATH


ARTIFACT_FILENAMES = (
    RESULT_FILENAME,
    STATIC_STRINGS_INFERENCE_RESULT_FILENAME,
    DYNAMIC_INFERENCE_RESULT_FILENAME,
    ENRICHMENT_FILENAME,
    REVERSING_AGENT_RESULT_FILENAME,
    REPORT_FILENAME,
)


def disk_status_by_sha256(sample_sha256: str) -> dict[str, Any] | None:
    if not WEB_ANALYSES_PATH.exists():
        return None

    for path in sorted(WEB_ANALYSES_PATH.iterdir()):
        if not path.is_dir():
            continue

        status = disk_analysis_status(path.name)
        if status and status.get("sample_sha256") == sample_sha256:
            return status

    return None


def disk_analysis_status(analysis_id: str) -> dict[str, Any] | None:
    analysis_dir = _disk_analysis_dir(analysis_id)
    if analysis_dir is None:
        return None

    artifact_dir = _find_artifact_dir(analysis_dir)
    analysis_data = load_json(artifact_dir, RESULT_FILENAME) or {}
    phases = _build_disk_phases(artifact_dir, analysis_data)
    filename = _resolve_sample_filename(analysis_id, analysis_data)
    resolved_sample_sha256 = _resolve_sample_sha256(artifact_dir, analysis_data)
    created_at = _directory_created_at(analysis_dir)

    return {
        "analysis_id": analysis_id,
        "status": "completed",
        "current_phase": None,
        "phases": phases,
        "error": None,
        "filename": filename,
        "pipeline_name": "full",
        "sample_sha256": resolved_sample_sha256,
        "output_dir": str(artifact_dir),
        "created_at": created_at,
    }


def _build_disk_phases(
    artifact_dir: Path,
    analysis_data: dict[str, Any],
) -> dict[str, str]:
    phases = _create_pending_phases()
    _complete_result_phases(phases, analysis_data)
    _complete_artifact_phases(phases, artifact_dir)

    return phases


def _create_pending_phases() -> dict[str, str]:
    phases = {}
    for phase in PHASES:
        phases[phase] = PhaseStatus.PENDING.value

    return phases


def _complete_result_phases(
    phases: dict[str, str],
    analysis_data: dict[str, Any],
) -> None:
    analysis_phases = analysis_data.get("phases")
    if not isinstance(analysis_phases, dict):
        return

    if analysis_phases.get("static"):
        phases["static"] = PhaseStatus.COMPLETED.value
    if analysis_phases.get("dynamic"):
        phases["dynamic"] = PhaseStatus.COMPLETED.value
    if analysis_phases.get("reversing"):
        phases["reverse_info"] = PhaseStatus.COMPLETED.value


def _complete_artifact_phases(
    phases: dict[str, str],
    artifact_dir: Path,
) -> None:
    phase_files = (
        ("static_inference", STATIC_STRINGS_INFERENCE_RESULT_FILENAME),
        ("dynamic_inference", DYNAMIC_INFERENCE_RESULT_FILENAME),
        ("enrichment", ENRICHMENT_FILENAME),
        ("reverse_agent", REVERSING_AGENT_RESULT_FILENAME),
        ("report", REPORT_FILENAME),
    )

    for phase, filename in phase_files:
        if (artifact_dir / filename).exists():
            phases[phase] = PhaseStatus.COMPLETED.value


def _analysis_sample(
    analysis_data: dict[str, Any],
) -> dict[str, Any]:
    sample = analysis_data.get("sample")
    if isinstance(sample, dict):
        return sample

    return {}


def _resolve_sample_filename(
    analysis_id: str,
    analysis_data: dict[str, Any],
) -> str:
    sample = _analysis_sample(analysis_data)
    sample_path = sample.get("path")

    if isinstance(sample_path, str):
        return Path(sample_path).name

    return analysis_id


def _resolve_sample_sha256(
    artifact_dir: Path,
    analysis_data: dict[str, Any],
) -> str:
    sample = _analysis_sample(analysis_data)
    sample_sha256 = sample.get("sha256")

    if isinstance(sample_sha256, str):
        return sample_sha256

    return artifact_dir.name


def _directory_created_at(path: Path) -> str:
    return format_modified_at(path.stat().st_mtime)


def _disk_analysis_dir(analysis_id: str) -> Path | None:
    root = WEB_ANALYSES_PATH.resolve()
    candidate = (WEB_ANALYSES_PATH / analysis_id).resolve()

    if not is_path_inside(root, candidate):
        raise HTTPException(
            status_code=400,
            detail="Invalid analysis id",
        )

    if not candidate.exists() or not candidate.is_dir():
        return None

    return candidate


def disk_artifact_dir(analysis_id: str) -> Path | None:
    analysis_dir = _disk_analysis_dir(analysis_id)
    if analysis_dir is None:
        return None

    return _find_artifact_dir(analysis_dir)


def _find_artifact_dir(analysis_dir: Path) -> Path:
    if _has_known_artifact(analysis_dir):
        return analysis_dir

    child_dirs = []
    candidates = []

    for path in analysis_dir.iterdir():
        if not path.is_dir():
            continue

        child_dirs.append(path)
        if _has_known_artifact(path):
            candidates.append(path)

    if candidates:
        return _most_recent_path(candidates)

    if len(child_dirs) == 1:
        return child_dirs[0]

    return analysis_dir


def _most_recent_path(paths: list[Path]) -> Path:
    most_recent = paths[0]
    most_recent_time = most_recent.stat().st_mtime

    for path in paths[1:]:
        modified_time = path.stat().st_mtime
        if modified_time > most_recent_time:
            most_recent = path
            most_recent_time = modified_time

    return most_recent


def _has_known_artifact(path: Path) -> bool:
    for filename in ARTIFACT_FILENAMES:
        if (path / filename).exists():
            return True

    return False
