from typing import Any


def parse_address(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if not isinstance(value, str):
        return None

    normalized = value.strip()
    if normalized.lower().startswith("fcn."):
        normalized = normalized[4:]
        return _parse_address_value(normalized, 16)

    return _parse_address_value(normalized, 0)


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


def is_import_function(name: Any) -> bool:
    if not isinstance(name, str):
        return False
    
    return name.lower().startswith(("sym.imp.", "imp.", "reloc.", "fcn.imp."))


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


def _parse_address_value(value: str, base: int) -> int | None:
    if not value:
        return None

    try:
        address = int(value, base)
    except ValueError:
        return None

    return address if address >= 0 else None
