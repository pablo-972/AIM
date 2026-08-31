from typing import Any

from core.tools.reversing.analyzers.metadata import (
    entrypoints,
    functions,
    imports,
)
from core.tools.reversing.analyzers.sections import sections
from core.utils.address import format_address


def list_imports(sample: str) -> dict[str, Any]:
    items = []
    for item in imports(sample):
        items.append(
            {
                "name": item.get("name"),
                "library": item.get("libname"),
            }
        )

    return {
        "imports": items,
        "count": len(items),
    }


def list_functions(sample: str) -> dict[str, Any]:
    items = []
    for item in functions(sample):
        items.append(
            {
                "name": item.get("name"),
                "address": format_address(item.get("address")),
                "size": item.get("size"),
            }
        )

    return {
        "functions": items,
        "count": len(items),
    }


def list_sections(sample: str) -> dict[str, Any]:
    items = []
    for item in sections(sample):
        items.append(
            {
                "name": item.get("name"),
                "address": format_address(item.get("vaddr")),
                "size": item.get("vsize") or item.get("size"),
                "permissions": item.get("perm"),
            }
        )

    return {
        "sections": items,
        "count": len(items),
    }


def list_entrypoints(sample: str) -> dict[str, Any]:
    items = []
    for item in entrypoints(sample):
        items.append(
            {
                "address": format_address(item.get("vaddr")),
                "physical_address": format_address(item.get("paddr")),
                "type": item.get("type"),
            }
        )

    return {
        "entrypoints": items,
        "count": len(items),
    }
