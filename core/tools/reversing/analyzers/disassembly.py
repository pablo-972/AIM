from typing import Any

from core.tools.reversing.analyzers.common import (
    architecture_bits,
    find_containing_internal_function,
    first_dict,
    format_instruction_lines,
    format_instruction as format_radare_instruction,
    function_address,
    normalize_instructions,
    ops_from_pdfj,
    ops_from_pdj,
    parse_radare_address,
    resolve_internal_function,
    target_reference,
)
from core.tools.reversing.analyzers.session import R2Session


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
        requested_address = parse_radare_address(address)
        containing_function = find_containing_internal_function(
            r2,
            requested_address,
        )

        if containing_function is None:
            return _region_analysis(r2, requested_address)

        resolved_function = function_address(containing_function)
        info = r2.cmdj(f"afij @ {resolved_function}") or []
        disasm = r2.cmdj(f"pdfj @ {resolved_function}") or {}

        function_info = first_dict(info) or {}
        ops = ops_from_pdfj(disasm)
        bits = architecture_bits(r2, function_info)

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

        function_info = first_dict(info) or {}
        ops = ops_from_pdfj(disasm)
        bits = architecture_bits(r2, function_info)

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

    pd_ops = ops_from_pdj(ops)
    bits = architecture_bits(r2, None)

    return _build_analysis(
        mode="region",
        resolved_function=None,
        info=None,
        ops=pd_ops,
        bits=bits,
        truncated=True,
    )


def _build_analysis(
    mode: str,
    resolved_function: str | None,
    info: dict[str, Any] | None,
    ops: list[dict[str, Any]],
    bits: int,
    truncated: bool,
) -> dict[str, Any]:
    instructions = normalize_instructions(ops)
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
        "instructions": format_instruction_lines(instructions, bits),
        "start_address": start_address,
        "end_address": end_address,
        "truncated": truncated,
    }


def format_instruction(address: int, instruction: str, bits: int) -> str:
    return format_radare_instruction(address, instruction, bits)
