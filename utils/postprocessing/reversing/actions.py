from typing import Any

from utils.postprocessing.reversing.contracts import (
    CODE_FOLLOW_UP_TOOLS,
    NO_TOOL_ACTIONS,
    XREF_TOOLS,
)
from ai.runtime.validators import (
    normalize_tool_parameters,
    validate_tool_parameters,
)


class ReversingActionPolicy:
    def __init__(self, available_tools: dict[str, Any]) -> None:
        self.available_tools = available_tools

    def next_action(
        self,
        analysis: dict[str, Any],
        target: dict[str, Any],
        observation: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        action = analysis.get("action")
        parameters = analysis.get("parameters")
        if not isinstance(action, str):
            return "none", {}
        if not isinstance(parameters, dict):
            parameters = {}

        code_targets = self._code_targets(observation)
        has_code_target = bool(code_targets)

        if target["tool"] in XREF_TOOLS and has_code_target:
            return "function", {"function": code_targets[0]}

        if target["tool"] == "function" and action == "disassembly":
            confidence = analysis.get("confidence")
            instructions_count = observation.get("instructions_count")
            if (
                confidence not in {"medium", "high"}
                or not isinstance(instructions_count, int)
                or instructions_count < 3
            ):
                return "none", {}
            parameters = normalize_tool_parameters(action, parameters)

        if action in CODE_FOLLOW_UP_TOOLS and has_code_target:
            requested_function = parameters.get("function")
            if requested_function not in code_targets:
                parameters = self._parameters_for_code_target(
                    action,
                    parameters,
                    code_targets[0],
                )
                return action, parameters

        if (
            target["tool"] in XREF_TOOLS
            and not has_code_target
            and action in CODE_FOLLOW_UP_TOOLS
        ):
            return "none", {}

        if action in NO_TOOL_ACTIONS:
            return action, {}

        parameters = normalize_tool_parameters(action, parameters)
        tool_spec = self.available_tools.get(action)
        if (
            not isinstance(tool_spec, dict)
            or not validate_tool_parameters(parameters, tool_spec)
        ):
            return "none", {}

        return action, parameters

    def _code_targets(self, observation: dict[str, Any]) -> list[str]:
        values = observation.get("code_targets")
        if not isinstance(values, list):
            return []
        return [value for value in values if isinstance(value, str)]

    def _parameters_for_code_target(
        self,
        action: str,
        parameters: dict[str, Any],
        code_target: str,
    ) -> dict[str, Any]:
        normalized = {"function": code_target}
        max_instructions = parameters.get("max_instructions")
        if action == "disassembly" and isinstance(max_instructions, int):
            normalized["max_instructions"] = max_instructions
        return normalize_tool_parameters(action, normalized)
