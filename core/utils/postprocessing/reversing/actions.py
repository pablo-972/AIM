from typing import Any

from core.utils.postprocessing.reversing.contracts import NO_TOOL_ACTIONS
from core.ai.runtime.reversing.parameters import prepare_reversing_tool_parameters
from core.ai.runtime.tool_validator import validate_tool_parameters


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

        parameters = prepare_reversing_tool_parameters(action, parameters)

        if not self._valid_tool_call(action, parameters):
            return "none", {}

        return action, parameters

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
