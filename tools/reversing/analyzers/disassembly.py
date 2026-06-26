from typing import Any

from tools.reversing.analyzers.session import R2Session

DEFAULT_MAX_INSTRUCTIONS = 300
MIN_MAX_INSTRUCTIONS = 25
MAX_MAX_INSTRUCTIONS = 500


def function_details(sample: str, function: str) -> dict[str, Any]:
    if not function:
        raise ValueError("function is required")

    with R2Session(sample) as r2:
        resolved_function = _resolve_function(r2, function)
        info = r2.cmdj(f"afij @ {resolved_function}") or []
        disasm = r2.cmdj(f"pdfj @ {resolved_function}") or {}

    return {
        "function": function,
        "resolved_function": resolved_function,
        "info": info[0] if info else {},
        "instructions": [
            {
                "address": op.get("addr") or op.get("offset"),
                "type": op.get("type"),
                "opcode": op.get("opcode"),
                "disasm": op.get("disasm"),
                "size": op.get("size"),
                "bytes": op.get("bytes"),
                "jump": op.get("jump"),
                "fail": op.get("fail"),
                "ptr": op.get("ptr"),
                "refptr": op.get("refptr"),
                "refs": op.get("refs", []),
            }
            for op in disasm.get("ops", [])
        ],
    }


def disassembly(sample: str, function: str) -> dict[str, Any]:
    details = function_details(sample, function)

    return {
        "function": details["function"],
        "resolved_function": details["resolved_function"],
        "function_info": details["info"],
        "instructions": details["instructions"],
    }


def text_disassembly(
    sample: str,
    function: str,
    max_instructions: int = DEFAULT_MAX_INSTRUCTIONS,
) -> dict[str, Any]:
    if not isinstance(max_instructions, int):
        raise ValueError("max_instructions must be an integer")
    max_instructions = max(
        MIN_MAX_INSTRUCTIONS,
        min(max_instructions, MAX_MAX_INSTRUCTIONS),
    )

    details = function_details(sample, function)

    ops = details["instructions"]
    selected_ops = ops[:max_instructions]

    text = "\n".join(
        f"{op['address']:#x}: {op['disasm']}"
        for op in selected_ops
        if op.get("address") is not None and op.get("disasm")
    )
    addresses = [
        op["address"]
        for op in selected_ops
        if isinstance(op.get("address"), int)
    ]

    return {
        "function": function,
        "resolved_function": details["resolved_function"],
        "function_info": details["info"],
        "instructions_count": len(ops),
        "returned_instructions": len(selected_ops),
        "truncated": len(ops) > max_instructions,
        "start_address": hex(min(addresses)) if addresses else None,
        "end_address": hex(max(addresses)) if addresses else None,
        "disassembly": text,
    }


def _parse_address(value: str) -> int | None:
    try:
        return int(value, 0)
    except ValueError:
        return None


def _find_containing_function(
    functions: list[dict[str, Any]],
    address: int,
) -> dict[str, Any] | None:
    for function in functions:
        offset = function.get("offset") or function.get("addr")
        size = function.get("size") or 0
        if (
            isinstance(offset, int)
            and isinstance(size, int)
            and offset <= address < offset + max(size, 1)
        ):
            return function

    return None


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



