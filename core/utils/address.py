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


def format_address(value: Any) -> str | None:
    address = parse_address(value)
    if address is None:
        return None

    return hex(address)


def _parse_address_value(value: str, base: int) -> int | None:
    if not value:
        return None

    try:
        address = int(value, base)
    except ValueError:
        return None

    return address if address >= 0 else None
