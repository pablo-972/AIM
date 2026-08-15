from collections.abc import Callable
from typing import Any

from core.tools.reversing.analyzers.disassembly import disassembly
from core.tools.reversing.analyzers.metadata import (
    callees,
    callers,
    entrypoints,
    functions,
    imports,
)
from core.tools.reversing.analyzers.sections import inspect_section, sections
from core.tools.reversing.analyzers.xrefs import string_xrefs, import_xrefs

ReversingAgentTool = Callable[..., Any]


def get_string_xrefs(sample: str, value: str) -> dict[str, Any]:
    return string_xrefs(sample, value, include_all_strings=True)


def list_imports(sample: str) -> dict[str, Any]:
    items = [
        {
            "name": item.get("name"),
            "library": item.get("libname"),
        }
        for item in imports(sample)
    ]

    return {
        "imports": items,
        "count": len(items),
    }


def list_functions(sample: str) -> dict[str, Any]:
    items = [
        {
            "name": item.get("name"),
            "address": _format_address(item.get("address")),
            "size": item.get("size"),
        }
        for item in functions(sample)
    ]

    return {
        "functions": items,
        "count": len(items),
    }


def list_sections(sample: str) -> dict[str, Any]:
    items = [
        {
            "name": item.get("name"),
            "address": _format_address(item.get("vaddr")),
            "size": item.get("vsize") or item.get("size"),
            "permissions": item.get("perm"),
        }
        for item in sections(sample)
    ]

    return {
        "sections": items,
        "count": len(items),
    }


def list_entrypoints(sample: str) -> dict[str, Any]:
    items = [
        {
            "address": _format_address(item.get("vaddr")),
            "physical_address": _format_address(item.get("paddr")),
            "type": item.get("type"),
        }
        for item in entrypoints(sample)
    ]

    return {
        "entrypoints": items,
        "count": len(items),
    }


def _format_address(value: Any) -> str | None:
    if isinstance(value, int):
        return hex(value)
    if isinstance(value, str) and value:
        return value

    return None


REVERSING_AGENT_TOOLS: dict[str, ReversingAgentTool] = {
    "disassembly": disassembly,
    "callers": callers,
    "callees": callees,
    "inspect_section": inspect_section,
    "string_xrefs": get_string_xrefs,
    "import_xrefs": import_xrefs,
    "list_imports": list_imports,
    "list_functions": list_functions,
    "list_sections": list_sections,
    "list_entrypoints": list_entrypoints,
}

REVERSING_AGENT_TOOL_NAMES = list(REVERSING_AGENT_TOOLS)

