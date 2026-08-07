from typing import Any

from core.tools.reversing.analyzers.common import (
    resolve_code_target,
    target_reference,
)
from core.tools.reversing.analyzers.session import R2Session


def binary_info(sample: str) -> dict[str, Any]:
    with R2Session(sample) as r2:
        return r2.cmdj("ij") or {}


def entrypoints(sample: str) -> list[dict[str, Any]]:
    with R2Session(sample) as r2:
        items = r2.cmdj("iej") or []

    if not isinstance(items, list):
        return []

    result = []
    for item in items:
        if not isinstance(item, dict):
            continue

        result.append(
            {
                "vaddr": item.get("vaddr"),
                "paddr": item.get("paddr"),
                "baddr": item.get("baddr"),
                "laddr": item.get("laddr"),
                "haddr": item.get("haddr"),
                "type": item.get("type"),
            }
        )

    return result


def imports(sample: str) -> list[dict[str, Any]]:
    with R2Session(sample) as r2:
        items = r2.cmdj("iij") or []

    return [
        {
            "name": item.get("name"),
            "libname": item.get("libname"),
            "type": item.get("type"),
            "ordinal": item.get("ordinal"),
            "bind": item.get("bind"),
            "plt": item.get("plt"),
        }
        for item in items
    ]


def functions(sample: str) -> list[dict[str, Any]]:
    with R2Session(sample) as r2:
        items = r2.cmdj("aflj") or []

    return [
        {
            "name": item.get("name"),
            "address": item.get("offset") or item.get("addr"),
            "type": item.get("type"),
            "signature": item.get("signature"),
            "size": item.get("size"),
            "realsz": item.get("realsz"),
            "instructions": item.get("ninstrs"),
            "basic_blocks": item.get("nbbs"),
            "edges": item.get("edges"),
            "calltype": item.get("calltype"),
            "nargs": item.get("nargs"),
            "nlocals": item.get("nlocals"),
            "stackframe": item.get("stackframe"),
            "recursive": item.get("recursive"),
            "noreturn": item.get("noreturn"),
            "indegree": item.get("indegree"),
            "outdegree": item.get("outdegree"),
        }
        for item in items
    ]


def sections(sample: str) -> list[dict[str, Any]]:
    with R2Session(sample) as r2:
        items = r2.cmdj("iSj") or []

    if not isinstance(items, list):
        return []

    result = []
    for item in items:
        if not isinstance(item, dict):
            continue

        result.append(
            {
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
        )

    return result


def function_details(
    sample: str,
    address: str | None = None,
    function: str | None = None,
) -> dict[str, Any]:
    with R2Session(sample) as r2:
        resolved_function = resolve_code_target(r2, address, function)
        info = r2.cmdj(f"afij @ {resolved_function}") or []

    function_info = info[0] if info else {}
    offset = function_info.get("offset") or function_info.get("addr")
    size = function_info.get("size")

    start_address = None
    end_address = None

    if isinstance(offset, int):
        start_address = hex(offset)

        if isinstance(size, int):
            end_address = hex(offset + max(size, 0))

    return {
        "address": address,
        "function": function,
        "resolved_function": resolved_function,
        "function_info": function_info,
        "instructions_count": _instruction_count(function_info),
        "start_address": start_address,
        "end_address": end_address,
    }


def strings(sample: str) -> list[dict[str, Any]]:
    with R2Session(sample) as r2:
        items = r2.cmdj("izj") or []

    return [
        {
            "string": item.get("string"),
            "vaddr": item.get("vaddr"),
            "paddr": item.get("paddr"),
            "size": item.get("size"),
            "section": item.get("section"),
            "type": item.get("type"),
        }
        for item in items
    ]


def callers(
    sample: str,
    address: str | None = None,
    function: str | None = None,
) -> dict[str, Any]:
    with R2Session(sample) as r2:
        resolved_function = resolve_code_target(r2, address, function)
        items = r2.cmdj(f"axtj @ {resolved_function}") or []

    target = target_reference(address, function)
    return {
        **target,
        "resolved_function": resolved_function,
        "callers": [
            {
                "from": item.get("from"),
                "to": item.get("to"),
                "type": item.get("type"),
                "opcode": item.get("opcode"),
                "function": item.get("fcn_name"),
                "perm": item.get("perm"),
            }
            for item in items
        ],
    }


def callees(
    sample: str,
    address: str | None = None,
    function: str | None = None,
) -> dict[str, Any]:
    with R2Session(sample) as r2:
        resolved_function = resolve_code_target(r2, address, function)
        function_info = r2.cmdj(f"pdfj @ {resolved_function}") or {}

    calls = []
    for op in function_info.get("ops", []):
        if op.get("type") in {"call", "ucall", "icall"}:
            calls.append(op)

    target = target_reference(address, function)
    return {
        **target,
        "resolved_function": resolved_function,
        "callees": [
            {
                "call_address": op.get("addr") or op.get("offset"),
                "call_type": op.get("type"),
                "opcode": op.get("opcode"),
                "disasm": op.get("disasm"),
                "target_address": op.get("jump") or op.get("ptr"),
                "fallthrough": op.get("fail"),
                "refs": op.get("refs", []),
            }
            for op in calls
        ],
        "count": len(calls),
    }


def _instruction_count(function_info: dict[str, Any]) -> int | None:
    for key in ("ninstrs", "instructions_count", "nins"):
        value = function_info.get(key)

        if isinstance(value, int):
            return value

    return None
