from typing import Any

from utils.logger import Logger
from tools.results import ToolResult
from tools.runner.base import BaseToolRunner
from tools.static.manual import STATIC_MANUAL_TOOLS
from orchestrator.context import AnalysisContext


class StaticToolRunner(BaseToolRunner):
    ALLOWED_RUNNERS = {"run_static"}

    def run_static(self) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}

        for tool in self._resolve_tools():
            results[tool] = self._execute_tool(tool)

        return results

    def _execute_tool(self, mode: str) -> dict[str, Any]:
        Logger.info(f"Executing static tool: {mode}")

        tool = STATIC_MANUAL_TOOLS[mode]

        try:
            data = tool(str(self.sample))
        except Exception as exc:
            Logger.error(f"Static tool '{mode}' failed: {exc}")
            return ToolResult.failed(exc).to_dict()
        
        return ToolResult.ok(data).to_dict()

    def _resolve_tools(self) -> list[str]:
        tools = list(self.context.static_tools)
        if "full" in tools:
            return list(STATIC_MANUAL_TOOLS)

        unknown_tools = []
        for tool in tools:
            if tool not in STATIC_MANUAL_TOOLS:
                unknown_tools.append(tool)

        if unknown_tools:
            raise ValueError(f"Unknown static mode(s): {', '.join(unknown_tools)}")

        return tools

