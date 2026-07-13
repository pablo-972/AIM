from typing import Any

from core.utils.artifacts.extractor import JsonExtractor
from core.utils.preprocessing.static.pe import prepare_pe_enrichment_sources
from core.utils.preprocessing.static.virustotal import prepare_vt_enrichment_data


def prepare_static_enrichment_sources(result: dict[str, Any]) -> list[tuple[str, Any]]:
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
