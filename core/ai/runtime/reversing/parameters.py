from typing import Any

from core.utils.reversing.address import parse_address

CODE_ADDRESS_TOOLS = {"disassembly", "callers", "callees"}
DISCOVERY_TOOLS = {
    "list_imports",
    "list_functions",
    "list_sections",
    "list_entrypoints",
}


def normalize_reversing_tool_parameters(
    tool_name: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    if tool_name in CODE_ADDRESS_TOOLS:
        return _normalize_code_address(parameters)

    if tool_name == "inspect_section":
        return _keep_parameters(parameters, {"section"})

    if tool_name == "string_xrefs":
        return _keep_parameters(parameters, {"value"})

    if tool_name == "import_xrefs":
        return _keep_parameters(parameters, {"import_name"})

    if tool_name in DISCOVERY_TOOLS:
        return {}

    return dict(parameters)


def _normalize_code_address(parameters: dict[str, Any]) -> dict[str, Any]:
    normalized = _keep_parameters(parameters, {"address"})
    address = normalized.get("address")
    parsed_address = parse_address(address)

    if parsed_address is not None:
        normalized["address"] = hex(parsed_address)

    return normalized


def _keep_parameters(
    parameters: dict[str, Any],
    allowed: set[str],
) -> dict[str, Any]:
    filtered_parameters = {}
    for key, value in parameters.items():
        if key in allowed:
            filtered_parameters[key] = value

    return filtered_parameters
