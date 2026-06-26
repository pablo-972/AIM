
from typing import Any

from utils.preprocessing.chunks import prepare_generic_report_chunks
from utils.preprocessing.pe import prepare_pe_enrichment_sources, prepare_pe_report_chunks
from utils.preprocessing.virustotal import prepare_vt_enrichment_data, prepare_vt_report_chunks
from utils.artifacts.extractor import JsonExtractor


def prepare_strings_report_data(
    tool_data: dict[str, Any],
) -> dict[str, Any]:
    data = dict(tool_data)
    parsed_strings = data.pop("parsed_strings", [])
    data["parsed_strings_count"] = (
        len(parsed_strings) if isinstance(parsed_strings, list) else 0
    )

    return data


def prepare_tool_data(tool_name: str, tool_data: Any) -> Any:
    if tool_name == "strings" and isinstance(tool_data, dict):
        return prepare_strings_report_data(tool_data)

    return tool_data


def prepare_report_chunks(
    tool_name: str,
    tool_data: Any,
) -> list[Any]:
    prepared_data = prepare_tool_data(tool_name, tool_data)

    if tool_name == "pe" and isinstance(prepared_data, dict):
        return prepare_pe_report_chunks(prepared_data)

    if tool_name in {"vt", "virustotal"} and isinstance(prepared_data, dict):
        return prepare_vt_report_chunks(prepared_data)

    return prepare_generic_report_chunks(tool_name, prepared_data)


def prepare_static_enrichment_sources(
    result: dict[str, Any],
) -> list[tuple[str, Any]]:
    sources: list[tuple[str, Any]] = []
    extractor = JsonExtractor(result)

    file_data = extractor.get_tool_data("file")
    if file_data:
        sources.append(("static.file", {"file_type": file_data}))

    metadata = extractor.get_tool_data("metadata")
    if metadata:
        sources.append(("static.metadata", metadata))

    packer = extractor.get_tool_data("packer")
    if isinstance(packer, dict) and packer:
        sources.append(("static.packer", packer))

    strings = extractor.get_tool_data("strings")
    if isinstance(strings, dict) and strings:
        strings_data = dict(strings)
        parsed_strings = strings_data.pop("parsed_strings", [])
        strings_data["parsed_strings_count"] = len(parsed_strings)
        sources.append(("static.strings.filtered", strings_data))

    pe = extractor.get_tool_data("pe")
    if isinstance(pe, dict) and pe:
        sources.extend(
            (f"static.pe.{source_name}", source_data)
            for source_name, source_data in prepare_pe_enrichment_sources(pe)
        )

    vt = extractor.get_tool_data("vt") or extractor.get_tool_data("virustotal")
    if isinstance(vt, dict) and vt:
        sources.append(("static.virustotal", prepare_vt_enrichment_data(vt)))

    return sources


def prepare_static_inference_sources(
    static_inference_data: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    if not static_inference_data:
        return []

    extractor = JsonExtractor(static_inference_data)
    findings = extractor.get_static_inference_findings()
    if not findings:
        return []

    return [
        (
            f"static_strings_inference.findings.{index}",
            {
                "confidence": finding.get("confidence"),
                "text": finding.get("text"),
                "category": finding.get("category"),
                "tone": finding.get("tone"),
            },
        )
        for index, finding in enumerate(findings, start=1)
    ]
