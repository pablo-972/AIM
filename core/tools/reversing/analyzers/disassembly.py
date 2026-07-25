from typing import Any

from core.tools.reversing.analyzers.session import R2Session


def disassembly(sample: str, function: str) -> dict[str, Any]:
    details = _function_analysis(sample, function)

    return {
        "function": function,
        "resolved_function": details["resolved_function"],
        "function_info": details["info"],
        "instructions_count": len(details["instructions"]),
        "start_address": details["start_address"],
        "end_address": details["end_address"],
        "instructions": details["instructions"],
    }


def text_disassembly(
    sample: str,
    function: str,
) -> dict[str, Any]:
    details = _function_analysis(sample, function)
    ops = details["instructions"]

    text_lines = []
    addresses = []  

    for op in ops:
        address = op.get("address")
        disasm = op.get("disasm")

        if address is not None and disasm:
            text_lines.append(f"{address:#x}: {disasm}")

        if isinstance(address, int):
            addresses.append(address)

    text = "\n".join(text_lines)

    if addresses:
        start_address = hex(min(addresses))
        end_address = hex(max(addresses))
    else:
        start_address = details["start_address"]
        end_address = details["end_address"]

    return {
        "function": function,
        "resolved_function": details["resolved_function"],
        "function_info": details["info"],
        "instructions_count": len(ops),
        "returned_instructions": len(ops),
        "start_address": start_address,
        "end_address": end_address,
        "disassembly": text,
    }


def _function_analysis(sample: str, function: str) -> dict[str, Any]:
    if not function:
        raise ValueError("function is required")

    with R2Session(sample) as r2:
        resolved_function = _resolve_function(r2, function)
        info = r2.cmdj(f"afij @ {resolved_function}") or []
        disasm = r2.cmdj(f"pdfj @ {resolved_function}") or {}

    instructions = []
    for op in disasm.get("ops", []):
        instruction = {
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

        instructions.append(instruction)

    addresses = []
    for instruction in instructions:
        address = instruction.get("address")

        if isinstance(address, int):
            addresses.append(address)

    start_address = None
    end_address = None
    if addresses:
        start_address = hex(min(addresses))
        end_address = hex(max(addresses))


    return {
        "resolved_function": resolved_function,
        "info": info[0] if info else {},
        "instructions": instructions,
        "start_address": start_address,
        "end_address": end_address,
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





