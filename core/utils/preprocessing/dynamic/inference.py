from typing import Any

from core.utils.preprocessing.dynamic.autoruns import prepare_autoruns_diff_section
from core.utils.preprocessing.dynamic.procmon import prepare_procmon_sections
from core.utils.preprocessing.dynamic.registry import prepare_registry_diff_section
from core.utils.artifacts.extractor import JsonExtractor


def prepare_dynamic_inference_inputs(
    dynamic_results: dict[str, Any],
) -> list[dict[str, Any]]:
    inputs: list[dict[str, Any]] = []

    autoruns_data = _tool_data(dynamic_results, "autoruns")
    if isinstance(autoruns_data, dict):
        inputs.extend(prepare_autoruns_diff_section(autoruns_data))

    registry_data = _tool_data(dynamic_results, "registry")
    if isinstance(registry_data, dict):
        
        inputs.extend(prepare_registry_diff_section(registry_data))

    procmon_data = _tool_data(dynamic_results, "procmon")
    if isinstance(procmon_data, dict):
        inputs.extend(prepare_procmon_sections(procmon_data))

    return inputs


def prepare_dynamic_inference_sources(
    dynamic_inference_data: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    if not dynamic_inference_data:
        return []

    extractor = JsonExtractor(dynamic_inference_data)
    findings = extractor.get_dynamic_inference_findings()

    if not findings:
        return []

    dynamic_findings = []
    for index, finding in enumerate(findings, start=1):
        dynamic_findings.append(
            (
                f"dynamic_inference.findings.{index}",
                finding, 
            )
        )
    
    return dynamic_findings


def _tool_data(dynamic_results: dict[str, Any], tool_name: str) -> Any:
    result = dynamic_results.get(tool_name)
    if not isinstance(result, dict):
        return None

    if result.get("status") != "ok":
        return None

    return result.get("data")
