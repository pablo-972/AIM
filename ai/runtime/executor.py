from typing import Any
from collections.abc import Callable

from ai.runtime.validators import NO_TOOL_ACTIONS, validate_agent_step


ToolExecutor = Callable[[str, dict[str, Any]], dict[str, Any]]


class AgentStepExecutor:
    def __init__(self, available_tools: dict[str, Any]) -> None:
        self.available_tools: dict[str, Any] = available_tools


    def execute(
            self, 
            decision: dict[str, Any], 
            tool_executor: ToolExecutor
        ) -> tuple[str | None, dict[str, Any] | None]:
        if not validate_agent_step(decision, self.available_tools):
            return None, {
                "success": False,
                "error": "Invalid agent step",
            }

        action = decision.get("action")
        if not isinstance(action, str):
            return None, {"success": False, "error": "Agent action must be a string"}

        if action in NO_TOOL_ACTIONS:
            return action, None

        parameters = decision.get("parameters") or {}
        if not isinstance(parameters, dict):
            return action, {"success": False, "error": "Agent step parameters must be an object"}

        try:
            result = tool_executor(action, parameters)
        except Exception as exc:
            return action, {"success": False, "error": str(exc)}

        return action, result

    
    
