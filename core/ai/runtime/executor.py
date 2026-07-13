from typing import Any
from collections.abc import Callable

from core.ai.runtime.validators import (
    NO_TOOL_ACTIONS,
    normalize_tool_parameters,
    validate_agent_step,
    validate_tool_parameters,
)

ToolExecutor = Callable[[str, dict[str, Any]], dict[str, Any]]


class AgentStepExecutor:
    def __init__(self, available_tools: dict[str, Any]) -> None:
        self.available_tools: dict[str, Any] = available_tools

    def execute(
        self,
        decision: dict[str, Any],
        tool_executor: ToolExecutor,
    ) -> tuple[str | None, dict[str, Any] | None]:
        if not validate_agent_step(decision, self.available_tools):
            return None, self._error("Invalid agent step")
            
        action = decision.get("action")
        if not isinstance(action, str):
            return None, self._error("Agent action must be a string")

        if action in NO_TOOL_ACTIONS:
            return action, None

        parameters = decision.get("parameters")
        if not isinstance(parameters, dict):
            return action, self._error("Agent step parameters must be an object")

        return action, self.execute_tool(
            action,
            parameters,
            tool_executor,
        )

    def execute_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        tool_executor: ToolExecutor,
    ) -> dict[str, Any]:
        tool_spec = self.available_tools.get(tool_name)
        normalized_parameters = normalize_tool_parameters(tool_name, parameters)

        if not isinstance(tool_spec, dict):
            return self._error("Invalid agent tool call")

        if not validate_tool_parameters(normalized_parameters, tool_spec):
            return self._error(f"Invalid parameters for agent tool call: {tool_name}")

        try:
            result = tool_executor(tool_name, normalized_parameters)
        except Exception as exc:
            return self._error(str(exc))

        if not isinstance(result, dict):
            return self._error("Agent tool returned a non-object result")
        
        return result

    def _error(self, message: str) -> dict[str, Any]:
        return {
            "success": False,
            "error": message,
        }