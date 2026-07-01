from typing import Any

from tools.reversing.analyzers.session import R2Session


def xrefs(sample: str, function: str) -> dict[str, Any]:
    if not function:
        raise ValueError("function is required")

    with R2Session(sample) as r2:
        refs = r2.cmdj(f"axtj @ {function}") or []

    return {
        "function": function,
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
        
        matches = [
            item
            for item in items
            if query in str(item.get("string", "")).lower()
        ]

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

        matches = [
            item
            for item in items
            if query in str(item.get("name", "")).lower()
            or query in str(item.get("libname", "")).lower()
        ]

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
    return [
        {
            "from": item.get("from"),
            "to": item.get("to"),
            "type": item.get("type"),
            "opcode": item.get("opcode"),
            "function": item.get("fcn_name"),
        }
        for item in items
    ]