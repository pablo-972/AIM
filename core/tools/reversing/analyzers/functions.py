from typing import Any

from core.utils.postprocessing.reversing.functions import (
    find_containing_function,
    is_import_function,
    parse_address,
)


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
    parsed_address = parse_address(address)
    if parsed_address is None:
        raise ValueError(f"Invalid Radare2 code address: {address}")

    containing = find_containing_function(_functions(r2), parsed_address)

    if containing is not None:
        if is_import_function(containing.get("name")):
            raise ValueError(
                f"Imported function is not an internal code target: {address}"
            )

        offset = containing.get("offset") or containing.get("addr")
        if isinstance(offset, int):
            return hex(offset)

    return hex(parsed_address)


def resolve_internal_function(r2: Any, function: str) -> str:
    function_name = function.strip()
    if not function_name:
        raise ValueError("function is required")

    for item in _functions(r2):
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


def _functions(r2: Any) -> list[dict[str, Any]]:
    items = r2.cmdj("aflj") or []
    if not isinstance(items, list):
        return []

    functions = []
    for item in items:
        if isinstance(item, dict):
            functions.append(item)

    return functions
