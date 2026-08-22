from typing import Any
from collections.abc import Callable

from core.ai.runtime.tool_validator import validate_tool_parameters

ToolExecutor = Callable[[str, dict[str, Any]], dict[str, Any]]


class AgentStepExecutor:
    def __init__(self, available_tools: dict[str, Any]) -> None:
        self.available_tools: dict[str, Any] = available_tools

    def execute_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        tool_executor: ToolExecutor,
    ) -> dict[str, Any]:
        tool_spec = self.available_tools.get(tool_name)
        if not isinstance(tool_spec, dict):
            return self._error("Invalid agent tool call")

        if not validate_tool_parameters(parameters, tool_spec):
            return self._error(f"Invalid parameters for agent tool call: {tool_name}")

        try:
            result = tool_executor(tool_name, parameters)
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
