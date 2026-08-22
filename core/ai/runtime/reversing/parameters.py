from typing import Any

from core.utils.address import parse_address

CODE_ADDRESS_TOOLS = {"disassembly", "callers", "callees"}
DISCOVERY_TOOLS = {
    "list_imports",
    "list_functions",
    "list_sections",
    "list_entrypoints",
}
TARGET_PARAMETER_BY_TOOL = {
    "inspect_section": "section",
    "import_xrefs": "import_name",
    "string_xrefs": "value",
}
TARGET_VALUE_KEYS = (
    "address",
    "function",
    "name",
    "import_name",
    "value",
    "section",
    "query",
)


def prepare_reversing_tool_parameters(
    tool_name: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    if tool_name in CODE_ADDRESS_TOOLS:
        return _prepare_code_address(parameters)

    if tool_name in TARGET_PARAMETER_BY_TOOL:
        return _keep_parameters(parameters, {target_parameter_key(tool_name)})

    if tool_name in DISCOVERY_TOOLS:
        return {}

    return dict(parameters)


def target_parameter_key(tool_name: str) -> str:
    if tool_name in CODE_ADDRESS_TOOLS:
        return "address"

    return TARGET_PARAMETER_BY_TOOL.get(tool_name, "value")


def target_text(tool_name: str, parameters: dict[str, Any]) -> str | None:
    value = parameters.get(target_parameter_key(tool_name))
    if isinstance(value, str) and value.strip():
        return value.strip()

    string_values = []
    for value in parameters.values():
        if isinstance(value, str) and value.strip():
            string_values.append(value.strip())

    if len(string_values) == 1:
        return string_values[0]

    return None


def display_target_value(tool_name: Any, parameters: dict[str, Any]) -> Any:
    if not isinstance(parameters, dict):
        return None

    for key in TARGET_VALUE_KEYS:
        value = parameters.get(key)
        if isinstance(value, (str, int, float)) and str(value):
            return value

    scalar_values = []
    for value in parameters.values():
        if isinstance(value, (str, int, float)) and str(value):
            scalar_values.append(value)

    if len(scalar_values) == 1:
        return scalar_values[0]

    if isinstance(tool_name, str) and tool_name.startswith("list_"):
        return tool_name

    return None


def _prepare_code_address(parameters: dict[str, Any]) -> dict[str, Any]:
    prepared = _keep_parameters(parameters, {"address"})
    address = prepared.get("address")
    parsed_address = parse_address(address)

    if parsed_address is not None:
        prepared["address"] = hex(parsed_address)

    return prepared


def _keep_parameters(
    parameters: dict[str, Any],
    allowed: set[str],
) -> dict[str, Any]:
    filtered_parameters = {}
    for key, value in parameters.items():
        if key in allowed:
            filtered_parameters[key] = value

    return filtered_parameters
