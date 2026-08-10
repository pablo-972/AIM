from typing import Any

from core.tools.reversing.analyzers.common import (
    architecture_bits,
    format_instruction_lines,
    normalize_instructions,
    ops_from_pdj,
)
from core.tools.reversing.analyzers.session import R2Session


MAX_FUNCTIONS_PREVIEW = 10
MAX_STRINGS_PREVIEW = 20
MAX_DISASSEMBLY_PREVIEW = 24


def sections(sample: str) -> list[dict[str, Any]]:
    with R2Session(sample) as r2:
        items = r2.cmdj("iSj") or []

    normalized_sections = []

    for item in _dict_items(items):
        normalized_section = _normalize_section(item)
        normalized_sections.append(normalized_section)

    return normalized_sections


def inspect_section(sample: str, section: str) -> dict[str, Any]:
    section_name = section.strip()
    if not section_name:
        raise ValueError("section is required")

    with R2Session(sample) as r2:
        section_item = _find_section(r2, section_name)
        section_info = _normalize_section(section_item)
        permissions = _section_permissions(section_info.get("perm"))
        start, end = _section_range(section_info)

        function_items = _functions_in_range(r2.cmdj("aflj") or [], start, end)
        string_items = _strings_in_range(r2.cmdj("izj") or [], start, end)
        entrypoint_items = _entrypoints_in_range(r2.cmdj("iej") or [], start, end)
        disassembly_preview = _disassembly_preview(r2, start, permissions["execute"])

    return {
        "section": section_name,
        "matched_section": section_info,
        "classification": _classify_section(section_info, permissions),
        "permissions": permissions,
        "range": {
            "start": hex(start),
            "end": hex(end),
        },
        "summary": {
            "functions_count": len(function_items),
            "strings_count": len(string_items),
            "entrypoints_count": len(entrypoint_items),
        },
        "entrypoints": _entrypoints_preview(entrypoint_items),
        "functions_preview": _functions_preview(function_items),
        "strings_preview": _strings_preview(string_items),
        "disassembly_preview": disassembly_preview,
    }


def _find_section(r2: Any, section_name: str) -> dict[str, Any]:
    for item in _dict_items(r2.cmdj("iSj") or []):
        name = item.get("name")
        if isinstance(name, str) and name.lower() == section_name.lower():
            return item

    raise ValueError(f"Section not found: {section_name}")


def _normalize_section(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": item.get("name"),
        "vaddr": item.get("vaddr"),
        "paddr": item.get("paddr"),
        "size": item.get("size"),
        "vsize": item.get("vsize"),
        "perm": item.get("perm"),
        "flags": item.get("flags"),
        "type": item.get("type"),
        "entropy": item.get("entropy"),
    }


def _section_permissions(perm: Any) -> dict[str, bool]:
    value = perm if isinstance(perm, str) else ""
    return {
        "read": "r" in value,
        "write": "w" in value,
        "execute": "x" in value,
    }


def _classify_section(
    section: dict[str, Any],
    permissions: dict[str, bool],
) -> str:
    name = str(section.get("name") or "").lower()
    section_type = str(section.get("type") or "").lower()

    if permissions["write"] and permissions["execute"]:
        return "mixed_or_suspicious"
    if permissions["execute"]:
        return "code"
    if name in {".rsrc", "rsrc"} or "resource" in section_type:
        return "resource"
    if permissions["read"]:
        return "data"

    return "unknown"


def _section_range(section: dict[str, Any]) -> tuple[int, int]:
    start = section.get("vaddr")
    size = section.get("vsize")

    if not isinstance(size, int) or size <= 0:
        size = section.get("size")

    if not isinstance(start, int) or not isinstance(size, int) or size <= 0:
        raise ValueError("Section has no usable virtual range")

    return start, start + size


def _functions_in_range(
    items: Any,
    start: int,
    end: int,
) -> list[dict[str, Any]]:
    functions = []
    for item in _dict_items(items):
        address = item.get("offset")
        if not isinstance(address, int):
            address = item.get("addr")

        if isinstance(address, int) and start <= address < end:
            functions.append(item)

    return sorted(functions, key=lambda item: _int_value(item, "offset", "addr"))


def _strings_in_range(
    items: Any,
    start: int,
    end: int,
) -> list[dict[str, Any]]:
    strings = []
    for item in _dict_items(items):
        address = item.get("vaddr")
        if isinstance(address, int) and start <= address < end:
            strings.append(item)

    return sorted(strings, key=lambda item: _int_value(item, "vaddr"))


def _entrypoints_in_range(
    items: Any,
    start: int,
    end: int,
) -> list[dict[str, Any]]:
    entrypoints = []
    for item in _dict_items(items):
        address = item.get("vaddr")
        if isinstance(address, int) and start <= address < end:
            entrypoints.append(item)

    return sorted(entrypoints, key=lambda item: _int_value(item, "vaddr"))


def _disassembly_preview(
    r2: Any,
    start: int,
    executable: bool,
) -> list[str]:
    if not executable:
        return []

    ops = r2.cmdj(f"pdj {MAX_DISASSEMBLY_PREVIEW} @ {hex(start)}") or []
    instructions = normalize_instructions(ops_from_pdj(ops))
    bits = architecture_bits(r2, None)
    return format_instruction_lines(instructions, bits)


def _entrypoints_preview(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "vaddr": item.get("vaddr"),
            "paddr": item.get("paddr"),
            "type": item.get("type"),
        }
        for item in items
    ]


def _functions_preview(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    preview = sorted(
        items,
        key=lambda item: _int_value(item, "size", "realsz"),
        reverse=True,
    )

    return [
        {
            "name": item.get("name"),
            "address": item.get("offset") or item.get("addr"),
            "size": item.get("size"),
            "instructions": item.get("ninstrs"),
            "basic_blocks": item.get("nbbs"),
        }
        for item in preview[:MAX_FUNCTIONS_PREVIEW]
    ]


def _strings_preview(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "string": item.get("string"),
            "vaddr": item.get("vaddr"),
            "paddr": item.get("paddr"),
            "size": item.get("size"),
            "type": item.get("type"),
        }
        for item in items[:MAX_STRINGS_PREVIEW]
    ]


def _dict_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    items = []
    for item in value:
        if isinstance(item, dict):
            items.append(item)

    return items


def _int_value(item: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = item.get(key)

        if isinstance(value, int):
            return value

    return 0
