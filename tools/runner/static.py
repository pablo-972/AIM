from collections.abc import Callable
from typing import Any

from utils.logger import Logger
from tools.results import ToolResult
from tools.runner.base import BaseToolRunner
from tools.static.agent import save_threat_actor_messages
from tools.static.manual import STATIC_MANUAL_TOOLS
from orchestrator.context import AnalysisContext


StaticAgentTool = Callable[
    [dict[str, Any], dict[str, Any]],
    dict[str, Any],
]


class StaticToolRunner(BaseToolRunner):
    ALLOWED_RUNNERS = {"run_static"}

    def __init__(self, context: AnalysisContext) -> None:
        super().__init__(context)

    def run_static(self) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}

        for mode in self._resolve_modes():
            results[mode] = self._execute_tool(mode)

        return results

    def _execute_tool(self, mode: str) -> dict[str, Any]:
        Logger.info(f"Executing static tool: {mode}")
        tool = STATIC_MANUAL_TOOLS[mode]

        try:
            data = tool(str(self.sample))
            return ToolResult.ok(data).to_dict()
        except Exception as exc:
            Logger.error(f"Static tool '{mode}' failed: {exc}")
            return ToolResult.failed(exc).to_dict()

    def _resolve_modes(self) -> list[str]:
        modes = list(self.context.static_modes)
        if "full" in modes:
            return list(STATIC_MANUAL_TOOLS)

        unknown_modes = [mode for mode in modes if mode not in STATIC_MANUAL_TOOLS]
        if unknown_modes:
            raise ValueError(f"Unknown static mode(s): {', '.join(unknown_modes)}")

        return modes





class StaticAgentToolRunner:
    def __init__(self, context: AnalysisContext) -> None:
        self.context: AnalysisContext = context
        self._tools: dict[str, StaticAgentTool] = {
            "save_threat_actor_messages": self._save_threat_actor_messages,
        }

    def execute(
        self,
        tool_name: str,
        parameters: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        tool = self._tools[tool_name]
        return tool(parameters or {}, context or {})

    def _save_threat_actor_messages(
            self, 
            parameters: dict[str, Any], 
            tool_context: dict[str, Any]
        ) -> dict[str, Any]:
        return save_threat_actor_messages(self.context.output, parameters, tool_context)




