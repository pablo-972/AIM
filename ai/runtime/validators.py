import json
import re
from copy import deepcopy
from json import JSONDecodeError
from typing import Any

from exceptions import ProviderError


NO_TOOL_ACTIONS = {"none", None}


DEFAULT_AGENT_RESPONSE = {
    "thought": "LLM returned bad response",
    "confidence": "low",
    "action": "none",
    "parameters": {},
}


def validate_agent_step(step: dict[str, Any], available_tools: dict[str, Any]) -> bool:
    if not isinstance(step, dict):
        return False

    action = step.get("action")
    parameters = step.get("parameters") or {}

    if action in NO_TOOL_ACTIONS:
        return True

    if action not in available_tools:
        return False

    if not isinstance(parameters, dict):
        return False

    return validate_tool_parameters(parameters, available_tools[action])


def validate_tool_parameters(parameters: dict[str, Any], tool_spec: dict[str, Any]) -> bool:
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


def parse_llm_json_response(content: str | None, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    content = (content or "").strip()
    if not content:
        return deepcopy(fallback or DEFAULT_AGENT_RESPONSE)

    content = _strip_json_markdown_block(content)
    try:
        parsed = json.loads(content)
    except JSONDecodeError as exc:
        raise ProviderError(f"Invalid JSON from LLM: {content[:500]}") from exc

    if not isinstance(parsed, dict):
        raise ProviderError("Invalid JSON from LLM: expected object")

    return parsed


def _strip_json_markdown_block(content: str) -> str:
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", content, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return content
