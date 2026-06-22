from typing import Any

from tools.reversing.analyzers.session import R2Session


def xrefs(sample: str, value: str) -> dict[str, Any]:
    if not value:
        raise ValueError("value is required")

    with R2Session(sample) as r2:
        r2.cmd(f"s {value}")
        items = r2.cmdj("axtj") or []

    return {
        "target": value,
        "xrefs": [
            {
                "from": item.get("from"),
                "to": item.get("to"),
                "type": item.get("type"),
                "opcode": item.get("opcode"),
                "fcn_name": item.get("fcn_name"),
            }
            for item in items
        ],
    }


def string_xrefs(
        sample: str, 
        value: str, 
        include_all_strings: bool = False
    ) -> dict[str, Any]:
    if not value:
        raise ValueError("value is required")

    command = "izzj" if include_all_strings else "izj"

    with R2Session(sample) as r2:
        items = r2.cmdj(command) or []
        matches = [
            item
            for item in items
            if value.lower() in str(item.get("string", "")).lower()
        ]

        results: list[dict[str, Any]] = []

        for item in matches:
            address = item.get("vaddr") or item.get("paddr")
            if address is None:
                continue

            r2.cmd(f"s {address}")

            results.append(
                {
                    "string": item.get("string"),
                    "address": address,
                    "section": item.get("section"),
                    "xrefs": r2.cmdj("axtj") or [],
                }
            )

    return {
        "query": value,
        "matches": results,
    }


def import_xrefs(sample: str, import_name: str) -> dict[str, Any]:
    if not import_name:
        raise ValueError("import_name is required")

    with R2Session(sample) as r2:
        items = r2.cmdj("iij") or []
        matches = [
            item
            for item in items
            if import_name.lower() in str(item.get("name", "")).lower()
        ]

        results: list[dict[str, Any]] = []

        for item in matches:
            address = item.get("plt") or item.get("vaddr") or item.get("offset")
            if address is None:
                continue

            r2.cmd(f"s {address}")

            results.append(
                {
                    "import": item.get("name"),
                    "address": address,
                    "library": item.get("libname"),
                    "xrefs": r2.cmdj("axtj") or [],
                }
            )

    return {
        "query": import_name,
        "matches": results,
    }