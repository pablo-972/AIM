from typing import Any

from core.tools.reversing.analyzers.session import R2Session


def binary_info(sample: str) -> dict[str, Any]:
    with R2Session(sample) as r2:
        return {
            "binary_info": r2.cmdj("ij") or {},
            "entrypoints": r2.cmdj("iej") or [],
        }


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
            "address": item.get("addr"),
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


def function_details(sample: str, function: str) -> dict[str, Any]:
    if not function:
        raise ValueError("function is required")

    with R2Session(sample) as r2:
        resolved_function = _resolve_function(r2, function)
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


def callers(sample: str, function: str) -> dict[str, Any]:
    if not function:
        raise ValueError("function is required")

    with R2Session(sample) as r2:
        items = r2.cmdj(f"axtj @ {function}") or []

    return {
        "function": function,
        "callers": [
            {
                "from": item.get("from"),
                "function": item.get("fcn_name"),
                "to": item.get("to"),
                "type": item.get("type"),
                "opcode": item.get("opcode"),
                "perm": item.get("perm"),
            }
            for item in items
        ],
    }


def callees(sample: str, function: str) -> dict[str, Any]:
    if not function:
        raise ValueError("function is required")

    with R2Session(sample) as r2:
        function_info = r2.cmdj(f"pdfj @ {function}") or {}

    calls = []
    for op in function_info.get("ops", []):
        if op.get("type") in {"call", "ucall", "icall"}:
            calls.append(op)

    return {
        "function": function,
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


def _resolve_function(r2: Any, function: str) -> str:
    address = _parse_address(function)
    if address is None:
        return function

    raw_functions = r2.cmdj("aflj") or []
    functions = raw_functions if isinstance(raw_functions, list) else []
    containing = _find_containing_function(functions, address)

    if containing is not None:
        name = containing.get("name")
        offset = containing.get("offset") or containing.get("addr")

        if isinstance(name, str) and name:
            return name

        if isinstance(offset, int):
            return hex(offset)

    r2.cmd(f"af @ {hex(address)}")
    return hex(address)


def _parse_address(value: str) -> int | None:
    try:
        return int(value, 0)
    except (TypeError, ValueError):
        return None


def _instruction_count(function_info: dict[str, Any]) -> int | None:
    for key in ("ninstrs", "instructions_count", "nins"):
        value = function_info.get(key)

        if isinstance(value, int):
            return value

    return None


def _find_containing_function(
    functions: list[dict[str, Any]],
    address: int,
) -> dict[str, Any] | None:
    for function in functions:
        offset = function.get("offset") or function.get("addr")
        size = function.get("size") or 0

        if not isinstance(offset, int) or not isinstance(size, int):
            continue

        if offset <= address < offset + max(size, 1):
            return function

    return None


