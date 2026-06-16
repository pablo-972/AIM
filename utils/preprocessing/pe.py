from utils.preprocessing.chunks import chunk_large_value, json_size, make_report_chunk


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


def _pick_existing_keys(data: dict, keys: list[str]) -> dict:
    return {
        key: data.get(key)
        for key in keys
        if key in data and data.get(key) not in ({}, [], None)
    }


def _import_entry(dll_name: str, functions: list) -> dict:
    return {
        "dll": dll_name,
        "functions": functions,
    }


def prepare_pe_import_sources(pe_data: dict) -> list[tuple[str, dict]]:
    imports = pe_data.get("imports") or {}
    if not imports:
        return []

    sources = []
    current = []

    for dll_name, functions in imports.items():
        if not functions:
            continue

        entry = _import_entry(dll_name, functions)
        candidate = [*current, entry]

        if current and json_size(candidate) > PE_IMPORTS_CHUNK_SIZE:
            sources.append((f"imports.{len(sources) + 1}", {"imports": current}))
            current = [entry]
        else:
            current = candidate

        if json_size(current) > PE_IMPORTS_CHUNK_SIZE:
            sources.append((f"imports.{len(sources) + 1}", {"imports": current}))
            current = []

    if current:
        sources.append((f"imports.{len(sources) + 1}", {"imports": current}))

    return sources


def prepare_pe_report_chunks(pe_data: dict) -> list[dict]:
    chunks = []

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


def prepare_pe_enrichment_sources(pe_data: dict) -> list[tuple[str, dict]]:
    sources = []

    summary = _pick_existing_keys(pe_data, PE_SUMMARY_KEYS)
    if summary:
        sources.append(("summary", summary))

    sections = pe_data.get("sections")
    if sections:
        sources.append(("sections", sections))

    for section_name, imports in prepare_pe_import_sources(pe_data):
        sources.append((section_name, imports))

    for key in ["delay_imports", "exports", "resources"]:
        value = pe_data.get(key)
        if value:
            sources.append((key, value))

    return sources
