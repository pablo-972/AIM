import unicodedata
from typing import Any

from core.utils.postprocessing.reversing.address import parse_address


def escape_invisible_unicode(value: str) -> str:
    result = []

    for character in value:
        category = unicodedata.category(character)

        if category in {"Cc", "Cf"}:
            result.append(_unicode_escape(character))
        else:
            result.append(character)

    return "".join(result)


def resolve_code_target(
    r2: Any,
    address: str | None = None,
    function: str | None = None,
) -> str:
    if address and function:
        raise ValueError("address and function cannot be combined")
    if address:
        return resolve_address(r2, address)
    if function:
        return resolve_internal_function(r2, function)

    raise ValueError("address or function is required")


def resolve_address(r2: Any, address: str) -> str:
    parsed_address = parse_radare_address(address)
    containing = find_containing_internal_function(r2, parsed_address)

    if containing is not None:
        return function_address(containing)

    return hex(parsed_address)


def resolve_internal_function(r2: Any, function: str) -> str:
    function_name = function.strip()
    if not function_name:
        raise ValueError("function is required")

    for item in radare_functions(r2):
        name = item.get("name")
        address = item.get("offset") or item.get("addr")

        if name != function_name or not isinstance(address, int):
            continue

        if is_import_function(name):
            raise ValueError(
                f"Imported function is not an internal code target: {function}"
            )

        return hex(address)

    raise ValueError(f"Internal function not found: {function}")


def parse_radare_address(address: str) -> int:
    parsed_address = parse_address(address)
    if parsed_address is None:
        raise ValueError(f"Invalid Radare2 code address: {address}")

    return parsed_address


def find_containing_function(
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


def find_containing_internal_function(
    r2: Any,
    address: int,
) -> dict[str, Any] | None:
    functions = radare_functions(r2)
    containing = find_containing_function(functions, address)

    if containing is None:
        return None

    function_name = containing.get("name")
    if is_import_function(function_name):
        return None

    return containing


def is_import_function(name: Any) -> bool:
    if not isinstance(name, str):
        return False

    import_references = ("sym.imp.", "imp.", "reloc.", "fcn.imp.")
    return name.lower().startswith(import_references)


def radare_functions(r2: Any) -> list[dict[str, Any]]:
    items = r2.cmdj("aflj") or []
    if not isinstance(items, list):
        return []

    functions = []
    for item in items:
        if isinstance(item, dict):
            functions.append(item)

    return functions


def function_address(function: dict[str, Any]) -> str:
    address = function.get("offset")

    if not isinstance(address, int):
        address = function.get("addr")
    if not isinstance(address, int):
        raise ValueError("Function has no usable address")

    return hex(address)


def target_reference(
    address: str | None,
    function: str | None,
) -> dict[str, str]:
    target = {}

    if address is not None:
        target["address"] = address
    if function is not None:
        target["function"] = function

    return target


def first_dict(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, list) or not value:
        return None

    item = value[0]
    return item if isinstance(item, dict) else None


def architecture_bits(
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


def ops_from_pdfj(disasm: Any) -> list[dict[str, Any]]:
    if not isinstance(disasm, dict):
        return []

    ops = disasm.get("ops")
    return ops_from_pdj(ops)


def ops_from_pdj(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    operations = []
    for operation in value:
        if isinstance(operation, dict):
            operations.append(operation)

    return operations


def normalize_instructions(ops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    instructions = []
    for op in ops:
        if not isinstance(op, dict):
            continue

        address = instruction_address(op)
        text = instruction_text(op)

        if address is None or not text:
            continue

        instructions.append(
            {
                "address": address,
                "size": instruction_size(op),
                "text": text,
            }
        )

    return instructions


def format_instruction_lines(
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


def instruction_address(op: dict[str, Any]) -> int | None:
    address = op.get("addr")
    if not isinstance(address, int):
        address = op.get("offset")

    return address if isinstance(address, int) else None


def instruction_text(op: dict[str, Any]) -> str | None:
    disasm = op.get("disasm")
    if isinstance(disasm, str) and disasm.strip():
        return disasm

    opcode = op.get("opcode")
    if isinstance(opcode, str) and opcode.strip():
        return opcode

    return None


def instruction_size(op: dict[str, Any]) -> int:
    size = op.get("size")
    if isinstance(size, int) and size > 0:
        return size

    return 0


def _unicode_escape(character: str) -> str:
    codepoint = ord(character)
    if codepoint <= 0xFFFF:
        return f"\\u{codepoint:04x}"

    return f"\\U{codepoint:08x}"
