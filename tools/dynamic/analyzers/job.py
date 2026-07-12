import shutil
import time
from pathlib import Path
from typing import Any

from config import (
    DYNAMIC_ARTIFACTS_PATH,
    DYNAMIC_EXECUTION_PATH,
    get_env, 
    VICTIM_WORKING_PATH, 
    DYNAMIC_JOB_FILENAME,
)
from exceptions import ToolError
from utils.io.files import save_json, save_pmc
from tools.dynamic.analyzers.autoruns import parse_autoruns_artifacts
from tools.dynamic.analyzers.procmon import parse_procmon_artifacts
from tools.dynamic.analyzers.registry import parse_registry_artifacts
from tools.dynamic.manual import build_dynamic_tools_config

RECEIVER_BASE_URL = get_env("AIM_DYNAMIC_ANALYSIS_BASE_URL")
RECEIVER_TIMEOUT = get_env("AIM_DYNAMIC_ANALYSIS_TIMEOUT")


def build_dynamic_job(
    sample: Path,
    sha256: str,
    selected_tools: list[str],
    procmon_filter: Path | None = None,
) -> dict[str, Any]:
    procmon_filter_config = None
    if procmon_filter:
        procmon_filter_config = procmon_filter.name

    return {
        "sample": {
            "filename": sample.name,
            "sha256": sha256,
            "working_dir": VICTIM_WORKING_PATH,
        },
        "receiver": {
            "base_url": RECEIVER_BASE_URL,
            "timeout": RECEIVER_TIMEOUT 
        },
        "tools": build_dynamic_tools_config(
            selected_tools,
            procmon_filter_config=procmon_filter_config,
        ),
    }


def prepare_dynamic_files(
    sample: Path,
    config: dict[str, Any],
    procmon_filter: Path | None = None,
) -> dict[str, Any]:
    execution_path = DYNAMIC_EXECUTION_PATH
    artifacts_path = DYNAMIC_ARTIFACTS_PATH
    _clear_previous_dynamic_analysis(execution_path)
    _clear_previous_dynamic_analysis(artifacts_path)

    sample_path = execution_path / sample.name
    config_path = execution_path / DYNAMIC_JOB_FILENAME

    shutil.copy2(sample, sample_path)
    _prepare_dynamic_tool_files(execution_path, config, procmon_filter)
    save_json(execution_path, DYNAMIC_JOB_FILENAME, config)

    return {
        "execution_path": str(execution_path),
        "artifacts_path": str(artifacts_path),
        "config_path": str(config_path),
        "sample_path": str(sample_path),
    }


def wait_for_dynamic_artifacts(
    config: dict[str, Any],
    timeout: int,
    poll_interval: float = 2.0,
) -> dict[str, Any]:
    expected = _expected_artifacts(config)
    deadline = time.monotonic() + timeout
    
    while time.monotonic() < deadline:
        missing = [path for path in expected if not path.exists()]
        if not missing:
            return {
                "status": "completed",
                "artifacts": [str(path) for path in expected],
            }
            
        time.sleep(poll_interval)

    missing = [path for path in expected if not path.exists()]

    raise ToolError(
        "Dynamic artifacts did not arrive before timeout: "
        + ", ".join(str(path) for path in missing)
    )


def parse_dynamic_artifacts(
    config: dict[str, Any],
    sample: Path,
) -> dict[str, Any]:
    tools = config.get("tools")
    if not isinstance(tools, dict):
        return {}

    parsed: dict[str, Any] = {}
    for name, tool_config in tools.items():
        if not isinstance(tool_config, dict) or not tool_config.get("enabled"):
            continue

        tool_name = str(name)
        if tool_name == "autoruns":
            parsed[tool_name] = parse_autoruns_artifacts(DYNAMIC_ARTIFACTS_PATH / "autoruns")
        elif tool_name == "registry":
            parsed[tool_name] = parse_registry_artifacts(DYNAMIC_ARTIFACTS_PATH / "registry")
        elif tool_name == "procmon":
            parsed[tool_name] = parse_procmon_artifacts(DYNAMIC_ARTIFACTS_PATH / "procmon", sample)

    return parsed


def _expected_artifacts(config: dict[str, Any]) -> list[Path]:
    tools = config.get("tools")
    if not isinstance(tools, dict):
        return []

    artifacts: list[Path] = []
    for name, tool_config in tools.items():
        if not isinstance(tool_config, dict) or not tool_config.get("enabled"):
            continue

        tool_name = str(name)
        params = tool_config.get("parameters")

        if not isinstance(params, dict):
            params = {}

        if tool_name == "autoruns":
            artifacts.extend(
                [
                    DYNAMIC_ARTIFACTS_PATH / "autoruns" / "before_execution.csv",
                    DYNAMIC_ARTIFACTS_PATH / "autoruns" / "after_execution.csv",
                ]
            )
        elif tool_name == "registry":
            for phase in ("before_execution", "after_execution"):
                for key in _registry_keys(params):
                    artifacts.append(
                        DYNAMIC_ARTIFACTS_PATH
                        / "registry"
                        / phase
                        / f"{_safe_filename(key)}.reg"
                    )
        elif tool_name == "procmon":
            csv_file = str(params.get("csv_file") or "procmon.csv")
            artifacts.append(DYNAMIC_ARTIFACTS_PATH / "procmon" / csv_file)

    return artifacts


def _prepare_dynamic_tool_files(
    execution_path: Path,
    config: dict[str, Any],
    procmon_filter: Path | None,
) -> None:
    procmon_params = _enabled_tool_parameters(config, "procmon")
    if not procmon_params:
        return

    filter_config = procmon_params.get("filter_config")
    if filter_config and procmon_filter:
        save_pmc(execution_path, str(filter_config), procmon_filter.read_bytes())


def _enabled_tool_parameters(config: dict[str, Any], tool_name: str) -> dict[str, Any] | None:
    tools = config.get("tools")
    if not isinstance(tools, dict):
        return None

    for name, tool_config in tools.items():
        normalized_name = str(name)
        if normalized_name != tool_name:
            continue
        
        if not isinstance(tool_config, dict) or not tool_config.get("enabled"):
            continue

        params = tool_config.get("parameters")
        if isinstance(params, dict):
            return params
        
        return {}

    return None


def _registry_keys(params: dict[str, Any]) -> list[str]:
    keys = params.get("registry_keys")

    if isinstance(keys, list) and keys:
        return [str(key) for key in keys]
    
    return []


def _safe_filename(value: str) -> str:
    safe = []

    for char in value:
        if char.isalnum():
            safe.append(char)
        else:
            safe.append("_")

    return "".join(safe).strip("_")


def _clear_previous_dynamic_analysis(path: Path) -> None:
    for item in path.iterdir():

        if item.is_dir():
            shutil.rmtree(item)
            continue

        if item.is_file():
            item.unlink()
