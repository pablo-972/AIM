from typing import Any


def resolve_function(r2: Any, function: str) -> str:
    address = parse_address(function)
    if address is None:
        return function

    raw_functions = r2.cmdj("aflj") or []
    functions = raw_functions if isinstance(raw_functions, list) else []
    containing = find_containing_function(functions, address)

    if containing is not None:
        name = containing.get("name")
        offset = containing.get("offset") or containing.get("addr")

        if isinstance(name, str) and name:
            return name

        if isinstance(offset, int):
            return hex(offset)

    r2.cmd(f"af @ {hex(address)}")
    return hex(address)


def parse_address(value: str) -> int | None:
    try:
        return int(value, 0)
    except (TypeError, ValueError):
        return None


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
