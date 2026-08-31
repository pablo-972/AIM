from typing import Any

from core.tools.reversing.agent import REVERSING_AGENT_TOOL_NAMES


def build_reversing_tool_definitions(
    available_tools: dict[str, Any],
) -> list[dict[str, Any]]:
    definitions = []

    for name in REVERSING_AGENT_TOOL_NAMES:
        specification = available_tools.get(name)
        if not isinstance(specification, dict):
            continue

        definition = _tool_definition(name, specification)
        if definition is not None:
            definitions.append(definition)

    return definitions


def tool_calls_to_targets(
    tool_calls: Any,
    priority: int,
) -> list[dict[str, Any]]:
    targets = []
    if not isinstance(tool_calls, (list, tuple)):
        return targets

    for tool_call in tool_calls:
        name = getattr(tool_call, "name", None)
        arguments = getattr(tool_call, "arguments", None)

        if name not in REVERSING_AGENT_TOOL_NAMES or not isinstance(arguments, dict):
            continue

        target_priority, target_arguments = _target_priority(arguments, priority)
        targets.append(
            {
                "tool": name,
                "parameters": target_arguments,
                "priority": target_priority,
            }
        )

    return targets


def _tool_definition(
    name: str,
    specification: dict[str, Any],
) -> dict[str, Any] | None:
    description = specification.get("description")
    parameters = specification.get("parameters")
    if not isinstance(description, str) or not isinstance(parameters, dict):
        return None

    properties = {}
    required = []

    for parameter_name, parameter in parameters.items():
        if not isinstance(parameter_name, str) or not isinstance(parameter, dict):
            continue

        parameter_schema = {}
        for key, value in parameter.items():
            if key != "required":
                parameter_schema[key] = value

        properties[parameter_name] = parameter_schema
        
        if parameter.get("required") is True:
            required.append(parameter_name)

    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


def _target_priority(
    arguments: dict[str, Any],
    default_priority: int,
) -> tuple[int, dict[str, Any]]:
    target_arguments = dict(arguments)
    value = target_arguments.pop("priority", default_priority)

    try:
        priority = int(value)
    except (TypeError, ValueError):
        priority = default_priority

    return max(1, min(priority, 100)), target_arguments


