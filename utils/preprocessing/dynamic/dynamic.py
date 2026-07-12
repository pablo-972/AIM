from typing import Any

from utils.preprocessing.dynamic.autoruns import prepare_autoruns_diff_chunks
from utils.preprocessing.dynamic.procmon import prepare_procmon_chunks
from utils.preprocessing.dynamic.registry import prepare_registry_diff_chunks

DYNAMIC_BATCH_SIZE = 5


def prepare_dynamic_inference_inputs(
    dynamic_results: dict[str, Any],
    batch_size: int = DYNAMIC_BATCH_SIZE,
) -> list[dict[str, Any]]:
    inputs: list[dict[str, Any]] = []

    autoruns_data = _tool_data(dynamic_results, "autoruns")
    if isinstance(autoruns_data, dict):
        inputs.extend(prepare_autoruns_diff_chunks(autoruns_data, batch_size))

    registry_data = _tool_data(dynamic_results, "registry")
    if isinstance(registry_data, dict):
        inputs.extend(prepare_registry_diff_chunks(registry_data, batch_size))

    procmon_data = _tool_data(dynamic_results, "procmon")
    if isinstance(procmon_data, dict):
        inputs.extend(prepare_procmon_chunks(procmon_data, batch_size))

    return inputs


def _tool_data(dynamic_results: dict[str, Any], tool_name: str) -> Any:
    result = dynamic_results.get(tool_name)
    if not isinstance(result, dict):
        return None

    if result.get("status") != "ok":
        return None

    return result.get("data")
