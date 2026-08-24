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


def target_dedup_key(tool_name: str, parameters: dict[str, Any]) -> str:
    target = display_target_value(tool_name, parameters)

    if tool_name in CODE_ADDRESS_TOOLS:
        address = parse_address(target)
        if address is not None:
            return f"{tool_name}:0x{address:x}"

    if tool_name == "import_xrefs":
        return f"{tool_name}:{_normalize_import_target(target)}"

    if tool_name == "string_xrefs":
        return f"{tool_name}:{_normalize_string_target(target)}"

    if isinstance(tool_name, str) and tool_name in DISCOVERY_TOOLS:
        return tool_name

    return f"{tool_name}:{target!r}"


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


def _normalize_import_target(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()

    return str(value)


def _normalize_string_target(value: Any) -> str:
    if not isinstance(value, str):
        return str(value)

    normalized = _strip_outer_quotes(value.strip())
    windows_candidate = _normalize_backslashes(normalized)

    if _is_windows_or_registry_target(windows_candidate):
        return windows_candidate.lower()

    return normalized


def _strip_outer_quotes(value: str) -> str:
    if len(value) < 2:
        return value

    first = value[0]
    last = value[-1]
    if first == last and first in {"'", '"'}:
        return value[1:-1].strip()

    return value


def _normalize_backslashes(value: str) -> str:
    while "\\\\" in value:
        value = value.replace("\\\\", "\\")

    return value


def _is_windows_or_registry_target(value: str) -> bool:
    if len(value) >= 3 and value[1] == ":" and value[2] == "\\":
        return value[0].isalpha()

    return _looks_like_registry_path(value)


def _looks_like_registry_path(value: str) -> bool:
    if value.startswith("\\"):
        return False

    parts = [
        part
        for part in value.split("\\")
        if part
    ]
    if len(parts) < 3:
        return False

    root = parts[0]
    if len(root) == 2 and root[1] == ":":
        return False

    return root.isidentifier()


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
