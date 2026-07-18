from typing import Any

from core.utils.preprocessing.dynamic.autoruns import prepare_autoruns_diff_section
from core.utils.preprocessing.dynamic.procmon import prepare_procmon_sections
from core.utils.preprocessing.dynamic.registry import prepare_registry_diff_section
from core.utils.artifacts.extractor import JsonExtractor


PROCMON_GROUP_SECTIONS = (
    "processes.created",
    "processes.terminated",
    "processes.loaded_images",
    "filesystem.created",
    "filesystem.modified",
    "filesystem.deleted",
    "filesystem.renamed",
    "registry.created",
    "registry.modified",
    "registry.deleted",
    "network.connections",
    "network.dns",
)
MAX_PROCMON_GROUPS_PER_SOURCE = 30


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
    findings = extractor.get_findings("dynamic_behavior")

    if not findings:
        return []

    dynamic_findings = []
    for index, finding in enumerate(findings, start=1):
        explanation = finding.get("explanation")
        if not isinstance(explanation, str) or not explanation.strip():
            continue

        dynamic_findings.append(
            (
                f"dynamic_inference.explanations.{index}",
                {
                    "explanation": explanation.strip(),
                },
            )
        )
    
    return dynamic_findings


def prepare_dynamic_artifact_sources(
    analysis_data: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    dynamic_tools = _dynamic_tools(analysis_data)
    sources: list[tuple[str, dict[str, Any]]] = []

    autoruns_data = _tool_data(dynamic_tools, "autoruns")
    if isinstance(autoruns_data, dict):
        sources.extend(_diff_sources("autoruns", autoruns_data))

    registry_data = _tool_data(dynamic_tools, "registry")
    if isinstance(registry_data, dict):
        sources.extend(_diff_sources("registry", registry_data))

    procmon_data = _tool_data(dynamic_tools, "procmon")
    if isinstance(procmon_data, dict):
        sources.extend(_procmon_group_sources(procmon_data))

    return sources


def _tool_data(dynamic_results: dict[str, Any], tool_name: str) -> Any:
    result = dynamic_results.get(tool_name)
    if not isinstance(result, dict):
        return None

    if result.get("status") != "ok":
        return None

    return result.get("data")


def _dynamic_tools(analysis_data: dict[str, Any]) -> dict[str, Any]:
    phases = analysis_data.get("phases")
    if not isinstance(phases, dict):
        return {}

    dynamic = phases.get("dynamic")
    if not isinstance(dynamic, dict):
        return {}

    tools = dynamic.get("tools")
    return tools if isinstance(tools, dict) else {}


def _diff_sources(
    tool_name: str,
    tool_data: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    diff = tool_data.get("diff")
    if not isinstance(diff, list) or not diff:
        return []

    sources = []
    total = len(diff)
    for index, item in enumerate(diff, start=1):
        sources.append(
            (
                f"dynamic.{tool_name}.diff.{index}",
                {
                    "tool": tool_name,
                    "type": "diff",
                    "index": index,
                    "total": total,
                    "diff": item,
                },
            )
        )

    return sources


def _procmon_group_sources(
    procmon_data: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    sources = []

    for section in PROCMON_GROUP_SECTIONS:
        collection = _section_data(procmon_data, section)
        if not isinstance(collection, dict):
            continue

        groups = collection.get("groups")
        if not isinstance(groups, list) or not groups:
            continue

        clean_groups = [
            group
            for group in groups
            if isinstance(group, dict)
        ]
        total_groups = len(clean_groups)

        for chunk_index, group_chunk in enumerate(
            _chunk_items(clean_groups, MAX_PROCMON_GROUPS_PER_SOURCE),
            start=1,
        ):
            source_name = f"dynamic.procmon.{section}.groups"
            if total_groups > MAX_PROCMON_GROUPS_PER_SOURCE:
                source_name = f"{source_name}.{chunk_index}"

            sources.append(
                (
                    source_name,
                    {
                        "tool": "procmon",
                        "section": section,
                        "chunk_index": chunk_index,
                        "group_count": len(group_chunk),
                        "total_groups": total_groups,
                        "total_items": collection.get("total"),
                        "truncated": collection.get("truncated"),
                        "groups": group_chunk,
                    },
                )
            )

    return sources


def _section_data(data: dict[str, Any], section: str) -> Any:
    current: Any = data

    for part in section.split("."):
        if not isinstance(current, dict):
            return None

        current = current.get(part)

    return current


def _chunk_items(items: list[dict[str, Any]], chunk_size: int) -> list[list[dict[str, Any]]]:
    size = max(1, chunk_size)
    return [
        items[index:index + size]
        for index in range(0, len(items), size)
    ]
