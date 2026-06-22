from typing import Any
from utils.logger import Logger
from tools.results import ToolResult
from tools.runner.base import BaseToolRunner
from tools.reversing.agent import REVERSING_AGENT_TOOLS
from tools.reversing.manual import REVERSING_MANUAL_TOOLS
from orchestrator.context import AnalysisContext


class ReversingToolRunner(BaseToolRunner):
    ALLOWED_RUNNERS = {"run_reversing"}

    def __init__(self, context: AnalysisContext) -> None:
        super().__init__(context)


    def _resolve_modes(self) -> list[str]:
        modes = list(self.context.reversing_modes)
        if "full" in modes:
            return ["info", "imports", "strings"]

        unknown_modes = [mode for mode in modes if mode not in REVERSING_MANUAL_TOOLS]
        if unknown_modes:
            raise ValueError(f"Unknown reverse mode(s): {', '.join(unknown_modes)}")

        return modes


    def _build_tool_kwargs(self, mode: str) -> dict[str, Any]:
        if mode == "disasm":
            return {"function": self.context.function}

        if mode == "xrefs":
            return {"function": self.context.function}

        if mode == "string-xrefs":
            return {"string_value": self.context.value}

        if mode == "import-xrefs":
            return {"import_name": self.context.value}

        if mode in {"callers", "callees"}:
            return {"function": self.context.function}

        return {}


    def _execute_tool(self, mode: str) -> dict[str, Any]:
        Logger.info(f"Executing reverse tool: {mode}")
        tool = REVERSING_MANUAL_TOOLS[mode]

        try:
            kwargs = self._build_tool_kwargs(mode)
            data = tool(str(self.sample), **kwargs)
            return ToolResult.ok(data).to_dict()
        except Exception as exc:
            Logger.error(f"Reverse tool '{mode}' failed: {exc}")
            return ToolResult.failed(exc).to_dict()


    def run_reversing(self) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}

        for mode in self._resolve_modes():
            results[mode] = self._execute_tool(mode)

        return results


class ReversingAgentToolRunner:
    def __init__(self, context: AnalysisContext) -> None:
        self.context: AnalysisContext = context

    def execute(
            self, 
            tool_name: str, 
            parameters: dict[str, Any] | None = None, 
            context: dict[str, Any] | None = None
        ) -> dict[str, Any]:
        tool = REVERSING_AGENT_TOOLS.get(tool_name)
        if tool is None:
            return {
                "success": False,
                "error": f"Unknown reversing agent tool: {tool_name}",
            }

        try:
            return {
                "success": True,
                "data": tool(str(self.context.sample), **(parameters or {})),
            }
        except Exception as exc:
            Logger.error(f"Reversing agent tool '{tool_name}' failed: {exc}")
            return {
                "success": False,
                "error": str(exc),
            }
