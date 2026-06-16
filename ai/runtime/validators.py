import json
from json import JSONDecodeError

from exceptions import ProviderError

NO_TOOL_ACTIONS = {"none", None}

DEFAULT_AGENT_RESPONSE = {
    "thought": "LLM returned bad response",
    "decision": "none",
    "confidence": "low",
    "action": "none",
    "parameters": {},
}


def validate_agent_step(step: dict, available_tools: dict) -> bool:
    if not isinstance(step, dict):
        return False

    tool_name = step.get("action")
    parameters = step.get("parameters", {})
    if tool_name in NO_TOOL_ACTIONS:
        return True

    if tool_name not in available_tools or not isinstance(parameters, dict):
        return False

    return validate_tool_parameters(parameters, available_tools[tool_name])


def validate_tool_parameters(parameters: dict, tool_spec: dict) -> bool:
    parameter_spec = tool_spec.get("parameters", {})
    if not isinstance(parameter_spec, dict):
        return True

    allowed_parameters = set(parameter_spec)
    unknown_parameters = set(parameters) - allowed_parameters
    if unknown_parameters:
        return False

    required_parameters = {
        name
        for name, spec in parameter_spec.items()
        if isinstance(spec, dict) and spec.get("required")
    }

    return required_parameters.issubset(parameters)


def parse_llm_json_response(content: str | None, fallback: dict | None = None) -> dict:
    content = (content or "").strip()
    if not content:
        return fallback or DEFAULT_AGENT_RESPONSE.copy()
    try:
        return json.loads(content)
    except JSONDecodeError as e:
        raise ProviderError(f"Invalid JSON from LLM: {content[:500]}") from e
