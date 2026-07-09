import json
import os
import shutil
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from exceptions import ToolError
from tools.dynamic.manual import build_dynamic_tools_config

DEFAULT_CONTROLLER_BASE_URL = "http://192.168.56.10:8080"
DEFAULT_CONTROLLER_TIMEOUT = 60
DEFAULT_SHARED_DIR = Path(__file__).resolve().parents[3] / "shared"
DEFAULT_WORKING_DIR = "desktop"

ENV_CONTROLLER_BASE_URL = "AIM_DYNAMIC_CONTROLLER_BASE_URL"
ENV_CONTROLLER_TIMEOUT = "AIM_DYNAMIC_CONTROLLER_TIMEOUT"
ENV_SHARED_DIR = "AIM_DYNAMIC_SHARED_DIR"


def build_dynamic_job(
    sample: Path,
    analysis_id: str,
    selected_tools: list[str],
) -> dict[str, Any]:
    return {
        "analysis_id": analysis_id,
        "sample": {
            "filename": sample.name,
            "sha256": analysis_id,
            "working_dir": DEFAULT_WORKING_DIR,
        },
        "controller": {
            "base_url": os.getenv(ENV_CONTROLLER_BASE_URL, DEFAULT_CONTROLLER_BASE_URL),
            "timeout": _env_int(ENV_CONTROLLER_TIMEOUT, DEFAULT_CONTROLLER_TIMEOUT),
        },
        "tools": build_dynamic_tools_config(selected_tools),
    }


def prepare_dynamic_job_files(
    sample: Path,
    analysis_id: str,
    job: dict[str, Any],
    shared_dir: Path | None = None,
) -> dict[str, Any]:
    shared_root = shared_dir or dynamic_shared_dir()
    job_dir = shared_root

    job_dir.mkdir(parents=True, exist_ok=True)
    _clear_previous_dynamic_job(job_dir)

    sample_target = job_dir / sample.name
    job_target = job_dir / "job.json"

    shutil.copy2(sample, sample_target)
    _save_json(job_target, job)

    return {
        "shared_dir": str(shared_root),
        "job_dir": str(job_dir),
        "job_path": str(job_target),
        "sample_path": str(sample_target),
        "result_path": str(dynamic_result_path(analysis_id, shared_root)),
    }


def wait_for_dynamic_result(
    analysis_id: str,
    timeout: int,
    shared_dir: Path | None = None,
    poll_interval: float = 2.0,
) -> dict[str, Any]:
    result_path = dynamic_result_path(analysis_id, shared_dir or dynamic_shared_dir())
    deadline = time.monotonic() + timeout
    last_status = "missing"

    while time.monotonic() < deadline:
        if result_path.exists():
            result = _load_json(result_path)
            last_status = _dynamic_result_state(result)
            if last_status in {"completed", "failed"}:
                return result
        time.sleep(poll_interval)

    raise ToolError(
        f"Dynamic result did not reach a terminal status before timeout "
        f"({last_status}): {result_path}"
    )


def check_collector_health(base_url: str, timeout: int) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError) as exc:
        return {
            "status": "unavailable",
            "url": url,
            "error": str(exc),
        }

    return {
        "status": "available",
        "url": url,
        "response": body,
    }


def dynamic_shared_dir() -> Path:
    value = os.getenv(ENV_SHARED_DIR)
    return Path(value).expanduser().resolve() if value else DEFAULT_SHARED_DIR


def dynamic_result_path(analysis_id: str, shared_dir: Path) -> Path:
    return shared_dir / "dynamic_result.json"


def _dynamic_result_state(result: dict[str, Any]) -> str:
    if result.get("errors"):
        return "failed"

    tools = result.get("tools")
    if not isinstance(tools, dict):
        return "waiting_tools"

    autoruns = tools.get("autoruns")
    if not isinstance(autoruns, dict):
        return "waiting_autoruns"

    data = autoruns.get("data")
    if not isinstance(data, dict):
        return "waiting_autoruns_data"

    if isinstance(data.get("after_execution"), list):
        return "completed"

    return "waiting_after_execution"


def _save_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ToolError(f"Dynamic result is not a JSON object: {path}")

    return data


def _clear_previous_dynamic_job(path: Path) -> None:
    for item in path.iterdir():
        if not item.is_file():
            continue

        if item.name in {"job.json", "dynamic_result.json"} or item.suffix.lower() != ".json":
            item.unlink()


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise ToolError(f"Invalid integer in {name}: {value}") from exc
