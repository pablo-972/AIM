from typing import Any

from core.tools.reversing.analyzers.functions import resolve_internal_function
from core.tools.reversing.analyzers.session import R2Session
from core.utils.postprocessing.reversing.functions import (
    escape_invisible_unicode,
    find_containing_function,
    is_import_function,
    parse_address,
    target_reference,
)


PD_INSTRUCTION_WINDOW = 80


def disassembly(
    sample: str,
    address: str | None = None,
    function: str | None = None,
) -> dict[str, Any]:
    details = _code_analysis(sample, address, function)
    target = target_reference(address, function)

    return {
        **target,
        "resolved_function": details["resolved_function"],
        "function_info": details["info"],
        "mode": details["mode"],
        "instructions_count": details["instructions_count"],
        "start_address": details["start_address"],
        "end_address": details["end_address"],
        "truncated": details["truncated"],
        "instructions": details["instructions"],
    }


def _code_analysis(
    sample: str,
    address: str | None,
    function: str | None,
) -> dict[str, Any]:
    if address and function:
        raise ValueError("address and function cannot be combined")
    if address:
        return _address_analysis(sample, address)
    if function:
        return _function_analysis(sample, function)

    raise ValueError("address or function is required")


def _address_analysis(
    sample: str,
    address: str,
) -> dict[str, Any]:
    with R2Session(sample) as r2:
        requested_address = _parse_requested_address(address)
        containing_function = _find_containing_internal_function(
            r2,
            requested_address,
        )

        if containing_function is None:
            return _region_analysis(r2, requested_address)

        resolved_function = _function_address(containing_function)
        info = r2.cmdj(f"afij @ {resolved_function}") or []
        disasm = r2.cmdj(f"pdfj @ {resolved_function}") or {}

        function_info = _first_dict(info) or {}
        ops = _ops_from_pdfj(disasm)
        bits = _architecture_bits(r2, function_info)

        return _build_analysis(
            mode="function",
            resolved_function=resolved_function,
            info=function_info,
            ops=ops,
            bits=bits,
            truncated=False,
        )


def _function_analysis(
    sample: str,
    function: str,
) -> dict[str, Any]:
    with R2Session(sample) as r2:
        resolved_function = resolve_internal_function(r2, function)
        info = r2.cmdj(f"afij @ {resolved_function}") or []
        disasm = r2.cmdj(f"pdfj @ {resolved_function}") or {}

        function_info = _first_dict(info) or {}
        ops = _ops_from_pdfj(disasm)
        bits = _architecture_bits(r2, function_info)

        return _build_analysis(
            mode="function",
            resolved_function=resolved_function,
            info=function_info,
            ops=ops,
            bits=bits,
            truncated=False,
        )


def _region_analysis(
    r2: Any,
    requested_address: int,
) -> dict[str, Any]:
    address = hex(requested_address)
    ops = r2.cmdj(f"pdj {PD_INSTRUCTION_WINDOW} @ {address}") or []

    pd_ops = _ops_from_pdj(ops)
    bits = _architecture_bits(r2, None)

    return _build_analysis(
        mode="region",
        resolved_function=None,
        info=None,
        ops=pd_ops,
        bits=bits,
        truncated=True,
    )


def _parse_requested_address(address: str) -> int:
    parsed_address = parse_address(address)
    if parsed_address is None:
        raise ValueError(f"Invalid Radare2 code address: {address}")

    return parsed_address


def _find_containing_internal_function(
    r2: Any,
    requested_address: int,
) -> dict[str, Any] | None:
    functions = r2.cmdj("aflj") or []
    if not isinstance(functions, list):
        functions = []

    valid_functions: list[dict[str, Any]] = []

    for function in functions:
        if isinstance(function, dict):
            valid_functions.append(function)

    containing = find_containing_function(valid_functions, requested_address)
    if containing is None:
        return None
    if is_import_function(containing.get("name")):
        return None

    return containing


def _function_address(function: dict[str, Any]) -> str:
    address = function.get("offset")
    if not isinstance(address, int):
        address = function.get("addr")
    if not isinstance(address, int):
        raise ValueError("Function has no usable address")

    return hex(address)


def _build_analysis(
    mode: str,
    resolved_function: str | None,
    info: dict[str, Any] | None,
    ops: list[dict[str, Any]],
    bits: int,
    truncated: bool,
) -> dict[str, Any]:
    instructions = _normal_instructions(ops)
    start_address = None
    end_address = None

    if instructions:
        first_address = instructions[0]["address"]
        last_instruction = instructions[-1]
        last_address = last_instruction["address"]
        last_size = last_instruction["size"]
        start_address = hex(first_address)
        end_address = hex(last_address + last_size)

    return {
        "mode": mode,
        "resolved_function": resolved_function,
        "info": info,
        "instructions_count": len(instructions),
        "instructions": _format_instructions(instructions, bits),
        "start_address": start_address,
        "end_address": end_address,
        "truncated": truncated,
    }


def _normal_instructions(ops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    instructions = []
    for op in ops:
        if not isinstance(op, dict):
            continue

        address = _instruction_address(op)
        text = _instruction_text(op)
        if address is None or not text:
            continue

        instructions.append(
            {
                "address": address,
                "size": _instruction_size(op),
                "text": text,
            }
        )

    return instructions


def _format_instructions(
    instructions: list[dict[str, Any]],
    bits: int,
) -> list[str]:
    lines = []
    for instruction in instructions:
        lines.append(
            format_instruction(
                instruction["address"],
                instruction["text"],
                bits,
            )
        )

    return lines


def format_instruction(address: int, instruction: str, bits: int) -> str:
    width = 16 if bits == 64 else 8
    safe_instruction = escape_invisible_unicode(instruction)
    return f"0x{address:0{width}x}: {safe_instruction}"


def _instruction_address(op: dict[str, Any]) -> int | None:
    address = op.get("addr")
    if not isinstance(address, int):
        address = op.get("offset")

    return address if isinstance(address, int) else None


def _instruction_text(op: dict[str, Any]) -> str | None:
    disasm = op.get("disasm")
    if isinstance(disasm, str) and disasm.strip():
        return disasm

    opcode = op.get("opcode")
    if isinstance(opcode, str) and opcode.strip():
        return opcode

    return None


def _instruction_size(op: dict[str, Any]) -> int:
    size = op.get("size")
    if isinstance(size, int) and size > 0:
        return size

    return 0


def _ops_from_pdfj(disasm: Any) -> list[dict[str, Any]]:
    if not isinstance(disasm, dict):
        return []

    ops = disasm.get("ops")
    return _ops_from_pdj(ops)


def _ops_from_pdj(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    operations: list[dict[str, Any]] = []
    for operation in value:
        if isinstance(operation, dict):
            operations.append(operation)

    return operations


def _first_dict(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, list) or not value:
        return None

    item = value[0]
    return item if isinstance(item, dict) else None


def _architecture_bits(
    r2: Any,
    function_info: dict[str, Any] | None,
) -> int:
    if isinstance(function_info, dict):
        bits = function_info.get("bits")
        if bits in {32, 64}:
            return bits

    info = r2.cmdj("ij") or {}
    if isinstance(info, dict):
        binary = info.get("bin")

        if isinstance(binary, dict):
            bits = binary.get("bits")
            if bits in {32, 64}:
                return bits

    return 32
