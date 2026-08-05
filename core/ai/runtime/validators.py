from typing import Any

from core.utils.postprocessing.reversing.functions import parse_address

NO_TOOL_ACTIONS = {"none", "finish"}


def normalize_tool_parameters(
    tool_name: str, 
    parameters: dict[str, Any],
) -> dict[str, Any]:
    if tool_name in {"disassembly", "callers", "callees"}:
        return _normalize_code_address(parameters)

    if tool_name == "string_xrefs":
        return _keep_parameters(parameters, {"value"})

    if tool_name == "import_xrefs":
        return _keep_parameters(parameters, {"import_name"})

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


def validate_agent_step(
    step: dict[str, Any], 
    available_tools: dict[str, Any],
) -> bool:
    if not isinstance(step, dict):
        return False

    action = step.get("action")
    parameters = step.get("parameters")

    if not isinstance(action, str):
        return False
    if not isinstance(parameters, dict):
        return False
    if action in NO_TOOL_ACTIONS:
        return True
    if action not in available_tools:
        return False

    return validate_tool_parameters(parameters, available_tools[action])


def validate_tool_parameters(
    parameters: dict[str, Any], 
    tool_spec: dict[str, Any],
) -> bool:
    parameter_spec = tool_spec.get("parameters", {})
    if not isinstance(parameter_spec, dict):
        return True

    allowed_parameters = set(parameter_spec)
    unknown_parameters = set(parameters) - allowed_parameters
    if unknown_parameters:
        return False

    required_parameters: set[str] = set()
    for name, spec in parameter_spec.items():
        if isinstance(spec, dict) and spec.get("required"):
            required_parameters.add(name)

    if not required_parameters.issubset(parameters):
        return False

    for name, value in parameters.items():
        spec = parameter_spec.get(name)
        if not isinstance(spec, dict):
            continue

        value_type = spec.get("type")
        if value_type == "integer" and not isinstance(value, int):
            return False
        if value_type == "string" and not isinstance(value, str):
            return False

        if name == "address" and parse_address(value) is None:
            return False

        minimum = spec.get("minimum")
        if isinstance(minimum, int) and isinstance(value, int) and value < minimum:
            return False

        maximum = spec.get("maximum")
        if isinstance(maximum, int) and isinstance(value, int) and value > maximum:
            return False

    return True
