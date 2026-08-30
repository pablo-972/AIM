from typing import Any

from core.ai.schemas.reversing import REVERSING_FINDING_SCHEMA
from core.tools.reversing.agent import REVERSING_AGENT_TOOL_NAMES


RECORD_FINDING_TOOL = "record_finding"
FINISH_INVESTIGATION_TOOL = "finish_investigation"


def build_reversing_tool_definitions(
    available_tools: dict[str, Any],
    include_finding_tools: bool,
) -> list[dict[str, Any]]:
    definitions = []

    for name in REVERSING_AGENT_TOOL_NAMES:
        specification = available_tools.get(name)
        if not isinstance(specification, dict):
            continue

        definition = _tool_definition(name, specification)
        if definition is not None:
            definitions.append(definition)

    if include_finding_tools:
        definitions.extend(_finding_tool_definitions())

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


def tool_call_finding(tool_calls: Any) -> dict[str, Any] | None:
    if not isinstance(tool_calls, (list, tuple)):
        return None

    for tool_call in tool_calls:
        if getattr(tool_call, "name", None) != RECORD_FINDING_TOOL:
            continue

        arguments = getattr(tool_call, "arguments", None)
        if not isinstance(arguments, dict):
            continue

        finding = arguments.get("finding")
        if isinstance(finding, dict):
            return finding

    return None


def tool_call_finish(tool_calls: Any) -> bool:
    if not isinstance(tool_calls, (list, tuple)):
        return False

    for tool_call in tool_calls:
        if getattr(tool_call, "name", None) == FINISH_INVESTIGATION_TOOL:
            return True

    return False


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

    properties["priority"] = {
        "type": "integer",
        "minimum": 1,
        "maximum": 100,
        "description": (
            "Optional scheduling priority for this investigation target. "
            "Use higher values for stronger concrete leads."
        ),
    }

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


def _finding_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": RECORD_FINDING_TOOL,
            "description": "Record one evidence-backed reversing finding.",
            "parameters": {
                "type": "object",
                "properties": {
                    "finding": REVERSING_FINDING_SCHEMA,
                },
                "required": ["finding"],
            },
        },
        {
            "name": FINISH_INVESTIGATION_TOOL,
            "description": "Finish this investigation when no further action is useful.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    ]
