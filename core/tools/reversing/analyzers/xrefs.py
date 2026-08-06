from typing import Any

from core.tools.reversing.analyzers.common import (
    resolve_code_target,
    target_reference,
)
from core.tools.reversing.analyzers.session import R2Session


def xrefs(
    sample: str,
    address: str | None = None,
    function: str | None = None,
) -> dict[str, Any]:
    with R2Session(sample) as r2:
        resolved_function = resolve_code_target(r2, address, function)
        refs = r2.cmdj(f"axtj @ {resolved_function}") or []

    target = target_reference(address, function)
    return {
        **target,
        "resolved_function": resolved_function,
        "xrefs": _normalize_xrefs(refs),
    }


def string_xrefs(
        sample: str, 
        value: str, 
        include_all_strings: bool = False
    ) -> dict[str, Any]:
    if not value:
        raise ValueError("value is required")

    results: list[dict[str, Any]] = []
    command = "izzj" if include_all_strings else "izj"
    query = value.lower()

    with R2Session(sample) as r2:
        items = r2.cmdj(command) or []
        matches: list[dict[str, Any]] = []

        for item in items:
            text = str(item.get("string", "")).lower()

            if query in text:
                matches.append(item)

        for item in matches:
            address = item.get("vaddr") or item.get("paddr")
            if address is None:
                continue
            
            refs = r2.cmdj(f"axtj @ {address}") or []

            results.append(
                {
                    "string": item.get("string"),
                    "address": address,
                    "section": item.get("section"),
                    "xrefs": _normalize_xrefs(refs),
                }
            )

    return {
        "query": value,
        "matches": results,
    }


def import_xrefs(sample: str, import_name: str) -> dict[str, Any]:
    if not import_name:
        raise ValueError("import_name is required")

    results: list[dict[str, Any]] = []
    query = import_name.lower()

    with R2Session(sample) as r2:
        items = r2.cmdj("iij") or []
        matches: list[dict[str, Any]] = []

        for item in items:
            name = str(item.get("name", "")).lower()
            library = str(item.get("libname", "")).lower()

            if query in name or query in library:
                matches.append(item)

        for item in matches:
            address = item.get("plt") or item.get("vaddr") or item.get("offset")
            if address is None:
                continue

            refs = r2.cmdj(f"axtj @ {address}") or []

            results.append(
                {
                    "import": item.get("name"),
                    "address": address,
                    "library": item.get("libname"),
                    "xrefs": _normalize_xrefs(refs),
                }
            )

    return {
        "query": import_name,
        "matches": results,
    }


def _normalize_xrefs(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_items: list[dict[str, Any]] = []

    for item in items:
        normalized_item = {
            "from": item.get("from"),
            "to": item.get("to"),
            "type": item.get("type"),
            "opcode": item.get("opcode"),
            "function": item.get("fcn_name"),
        }

        normalized_items.append(normalized_item)

    return normalized_items
