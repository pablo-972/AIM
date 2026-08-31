from typing import Any


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

        minimum = spec.get("minimum")
        if isinstance(minimum, int) and isinstance(value, int) and value < minimum:
            return False

        maximum = spec.get("maximum")
        if isinstance(maximum, int) and isinstance(value, int) and value > maximum:
            return False

    return True
