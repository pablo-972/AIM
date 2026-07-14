from typing import Any

from core.utils.preprocessing.chunks import chunk_large_value, json_size, make_report_chunk

PE_SUMMARY_KEYS = [
    "architecture",
    "sizes",
    "subsystem",
    "version_info",
]
PE_DIRECT_SECTION_KEYS = [
    "sections",
    "delay_imports",
    "exports",
    "resources",
]
PE_IMPORTS_CHUNK_SIZE = 2500


def prepare_pe_import_sources(pe_data: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    imports = pe_data.get("imports")
    if not isinstance(imports, dict) or not imports:
        return []

    sources: list[tuple[str, dict[str, Any]]] = []
    current: list[dict[str, Any]] = []

    for dll_name, functions in imports.items():
        if not functions:
            continue

        entry = _import_entry(dll_name, functions)

        if current and json_size([*current, entry]) > PE_IMPORTS_CHUNK_SIZE:
            _append_import_source(sources, current)
            current = []

        current.append(entry)

        if json_size(current) > PE_IMPORTS_CHUNK_SIZE:
            _append_import_source(sources, current)
            current = []

    if current:
        _append_import_source(sources, current)

    return sources


def prepare_pe_report_chunks(pe_data: dict[str, Any]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []

    summary = _pick_existing_keys(pe_data, PE_SUMMARY_KEYS)
    if summary:
        chunks.append(make_report_chunk("summary", summary))

    for key in PE_DIRECT_SECTION_KEYS:
        value = pe_data.get(key)
        if value:
            chunks.extend(chunk_large_value(key, value))

    for section_name, imports in prepare_pe_import_sources(pe_data):
        chunks.extend(chunk_large_value(section_name, imports))

    return chunks or [make_report_chunk("raw", pe_data)]


def prepare_pe_enrichment_sources(
    pe_data: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    sources: list[tuple[str, dict[str, Any]]] = []

    summary = _pick_existing_keys(pe_data, PE_SUMMARY_KEYS)
    if summary:
        sources.append(("summary", summary))

    sections = pe_data.get("sections")
    if sections:
        sources.append(("sections", {"sections": sections}))

    for section_name, imports in prepare_pe_import_sources(pe_data):
        sources.append((section_name, imports))

    for key in ["delay_imports", "exports", "resources"]:
        value = pe_data.get(key)
        if value:
            sources.append((key, {key: value}))

    return sources


def _pick_existing_keys(data: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {
        key: data.get(key)
        for key in keys
        if key in data and data.get(key) not in ({}, [], None)
    }


def _import_entry(dll_name: str, functions: list[Any]) -> dict[str, Any]:
    return {
        "dll": dll_name,
        "functions": functions,
    }


def _append_import_source(
    sources: list[tuple[str, dict[str, Any]]],
    imports: list[dict[str, Any]],
) -> None:
    sources.append(
        (
            f"imports.{len(sources) + 1}",
            {"imports": imports},
        )
    )