from typing import Any

from core.ai.runtime.reversing.parameters import display_target_value
from core.utils.address import format_address, parse_address


FOLLOW_UP_PRIORITY_BOOST = 5
EXTERNAL_CODE_PREFIXES = ("sym.imp.", "imp.", "reloc.", "fcn.imp.")


def deterministic_follow_ups(
    target: dict[str, Any],
    tool_output: dict[str, Any],
) -> list[dict[str, Any]]:
    tool_name = target.get("tool")
    data = tool_output.get("data")
    if not isinstance(tool_name, str) or not isinstance(data, dict):
        return []

    if tool_name in {"import_xrefs", "string_xrefs"}:
        return _xref_follow_ups(target, data)
    if tool_name == "disassembly":
        return _disassembly_follow_ups(target, data)

    return []


def deterministic_chunk_follow_ups(
    target: dict[str, Any],
    tool_output: dict[str, Any],
    chunk: Any,
) -> list[dict[str, Any]]:
    if target.get("tool") != "disassembly":
        return []

    full_data = tool_output.get("data")
    if not isinstance(full_data, dict):
        return []

    instructions = _chunk_instructions(chunk)
    if not instructions:
        return []

    return _disassembly_follow_ups(
        target,
        {
            "instructions": instructions,
            "start_address": full_data.get("start_address"),
            "end_address": full_data.get("end_address"),
        },
    )


def _xref_follow_ups(
    target: dict[str, Any],
    data: dict[str, Any],
) -> list[dict[str, Any]]:
    follow_ups = []

    for match in _dict_items(data.get("matches")):
        for xref in _dict_items(match.get("xrefs")):
            address = _xref_address(xref)
            if address is None:
                continue

            follow_ups.append(
                _follow_up_target(
                    target,
                    address,
                    str(xref.get("type") or "xref"),
                )
            )

    return follow_ups


def _xref_address(xref: dict[str, Any]) -> str | None:
    for key in ("function", "from", "address"):
        address = format_address(xref.get(key))
        if address is not None:
            return address

    return None


def _disassembly_follow_ups(
    target: dict[str, Any],
    data: dict[str, Any],
) -> list[dict[str, Any]]:
    follow_ups = []
    seen_addresses = set()
    current_start = parse_address(data.get("start_address"))
    current_end = parse_address(data.get("end_address"))

    for line in _instruction_lines(data.get("instructions")):
        relation, raw_target = _direct_code_reference(line)
        if relation is None or raw_target is None:
            continue
        if _is_external_code_target(raw_target):
            continue

        address = format_address(raw_target)
        if address is None:
            continue
        if address in seen_addresses:
            continue
        if (
            not _is_function_symbol(raw_target)
            and _inside_current_function(address, current_start, current_end)
        ):
            continue

        seen_addresses.add(address)
        follow_ups.append(
            _follow_up_target(
                target,
                address,
                relation,
            )
        )

    return follow_ups


def _follow_up_target(
    origin: dict[str, Any],
    address: str,
    relation: str,
) -> dict[str, Any]:
    return {
        "tool": "disassembly",
        "parameters": {
            "address": address,
        },
        "priority": _follow_up_priority(origin),
        "origin_tool": origin.get("tool"),
        "origin_target": _origin_target(origin),
        "discovered_target": address,
        "relation": relation,
    }


def _follow_up_priority(origin: dict[str, Any]) -> int:
    try:
        priority = int(origin.get("priority", 50))
    except (TypeError, ValueError):
        priority = 50

    return min(100, priority + FOLLOW_UP_PRIORITY_BOOST)


def _origin_target(target: dict[str, Any]) -> str | None:
    parameters = target.get("parameters")
    if not isinstance(parameters, dict):
        return None

    value = display_target_value(target.get("tool"), parameters)
    if isinstance(value, str) and value:
        return value

    return None


def _direct_code_reference(line: str) -> tuple[str | None, str | None]:
    _, separator, instruction = line.partition(":")
    if not separator:
        return None, None

    parts = instruction.strip().split()
    if len(parts) < 2:
        return None, None

    mnemonic = parts[0].lower()
    if mnemonic == "call":
        return "call", parts[1].rstrip(",")
    if mnemonic.startswith("j"):
        return "jump", parts[1].rstrip(",")

    return None, None


def _chunk_instructions(chunk: Any) -> list[str]:
    if not isinstance(chunk, dict):
        return []

    section = chunk.get("section")
    data = chunk.get("data")
    if not isinstance(section, str):
        return []
    if not section.startswith("disassembly.instructions."):
        return []

    return _instruction_lines(data)


def _inside_current_function(
    address: str,
    current_start: int | None,
    current_end: int | None,
) -> bool:
    parsed_address = parse_address(address)
    return (
        parsed_address is not None
        and current_start is not None
        and current_end is not None
        and current_start <= parsed_address < current_end
    )


def _is_external_code_target(value: str) -> bool:
    target_name = value.strip().lower()
    return (
        target_name.startswith(EXTERNAL_CODE_PREFIXES)
        or ".dll" in target_name
    )


def _is_function_symbol(value: str) -> bool:
    return value.strip().lower().startswith("fcn.")


def _instruction_lines(value: Any) -> list[str]:
    if isinstance(value, str):
        return [
            line.strip()
            for line in value.splitlines()
            if line.strip()
        ]

    if not isinstance(value, list):
        return []

    lines = []
    for item in value:
        if isinstance(item, str) and item.strip():
            lines.append(item)

    return lines


def _dict_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    items = []
    for item in value:
        if isinstance(item, dict):
            items.append(item)

    return items
