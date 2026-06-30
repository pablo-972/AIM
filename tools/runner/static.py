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

        for mode in self._resolve_modes():
            results[mode] = self._execute_tool(mode)

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

    def _resolve_modes(self) -> list[str]:
        modes = list(self.context.static_modes)
        if "full" in modes:
            return list(STATIC_MANUAL_TOOLS)

        unknown_modes = [mode for mode in modes if mode not in STATIC_MANUAL_TOOLS]
        if unknown_modes:
            raise ValueError(f"Unknown static mode(s): {', '.join(unknown_modes)}")

        return modes

