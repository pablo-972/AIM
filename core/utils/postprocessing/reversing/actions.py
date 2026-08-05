from typing import Any

from core.utils.postprocessing.reversing.contracts import (
    CODE_FOLLOW_UP_TOOLS,
    NO_TOOL_ACTIONS,
    XREF_TOOLS,
)
from core.ai.runtime.validators import (
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
        if not isinstance(action, str):
            return "none", {}
        if action in NO_TOOL_ACTIONS:
            return action, {}
        
        parameters = analysis.get("parameters")
        if not isinstance(parameters, dict):
            parameters = {}

        current_tool = target.get("tool")
        if not isinstance(current_tool, str):
            return "none", {}
        
        code_targets = self._code_targets(observation)
        has_code_target = bool(code_targets)

        if (
            current_tool in XREF_TOOLS
            and not has_code_target
            and action in CODE_FOLLOW_UP_TOOLS
        ):
            return "none", {}

        if current_tool in XREF_TOOLS and has_code_target:
            return "disassembly", {"address": code_targets[0]}

        if action in CODE_FOLLOW_UP_TOOLS and not parameters.get("address"):
            if has_code_target:
                return action, self._parameters_for_code_target(
                    action,
                    code_targets[0],
                )

        parameters = normalize_tool_parameters(action, parameters)
        
        if not self._valid_tool_call(action, parameters):
            return "none", {}

        return action, parameters


    def _code_targets(self, observation: dict[str, Any]) -> list[str]:
        values = observation.get("code_targets")

        if not isinstance(values, list):
            return []

        targets = []
        for value in values:
            if isinstance(value, str):
                targets.append(value)

        return targets

    def _parameters_for_code_target(
        self,
        action: str,
        code_target: str,
    ) -> dict[str, Any]:
        normalized = {
            "address": code_target,
        }
        
        return normalize_tool_parameters(action, normalized)

    def _valid_tool_call(
        self,
        action: str,
        parameters: dict[str, Any],
    ) -> bool:
        tool_spec = self.available_tools.get(action)

        return (
            isinstance(tool_spec, dict)
            and validate_tool_parameters(parameters, tool_spec)
        )
