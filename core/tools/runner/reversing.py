from typing import Any
from pathlib import Path

from core.utils.logger import Logger
from core.tools.results import ToolResult
from core.tools.runner.base import BaseToolRunner
from core.tools.reversing.agent import REVERSING_AGENT_TOOLS
from core.tools.reversing.manual import REVERSING_MANUAL_TOOLS


class ReversingToolRunner(BaseToolRunner):
    ALLOWED_RUNNERS = {"run_reversing"}

    def run_reversing(self) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}

        for tool in self._resolve_tools():
            results[tool] = self._execute_tool(tool)

        return results

    def _execute_tool(self, mode: str) -> dict[str, Any]:
        Logger.info(f"Executing reversing tool: {mode}")

        tool = REVERSING_MANUAL_TOOLS[mode]
        kwargs = self._build_tool_kwargs(mode)

        try:
            data = tool(str(self.sample), **kwargs)
        except Exception as exc:
            Logger.error(f"Reversing tool '{mode}' failed: {exc}")
            return ToolResult.failed(exc).to_dict()

        return ToolResult.ok(data).to_dict()

    def _resolve_tools(self) -> list[str]:
        tools = list(self.context.reversing_tools)
        if "full" in tools:
            return ["info", "imports"]

        unknown_tools = []
        for tool in tools:
            if tool not in REVERSING_MANUAL_TOOLS:
                unknown_tools.append(tool)

        if unknown_tools:
            raise ValueError(f"Unknown reversing mode(s): {', '.join(unknown_tools)}")

        return tools

    def _build_tool_kwargs(self, mode: str) -> dict[str, Any]:
        if mode == "disasm":
            return {"function": self.context.function}
        elif mode == "xrefs":
            return {"function": self.context.function}
        elif mode in {"callers", "callees"}:
            return {"function": self.context.function}
        elif mode == "string-xrefs":
            return {"string_value": self.context.value}
        elif mode == "import-xrefs":
            return {"import_name": self.context.value}

        return {}


class ReversingAgentToolRunner:
    def __init__(self, sample: Path) -> None:
        self.sample = str(sample)

    def execute(
        self, 
        tool_name: str, 
        parameters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        tool = REVERSING_AGENT_TOOLS[tool_name]

        return {
            "success": True,
            "data": tool(self.sample, **(parameters or {})),
        }
