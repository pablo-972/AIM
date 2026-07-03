from typing import Any
from pathlib import Path

from utils.logger import Logger
from tools.results import ToolResult
from tools.runner.base import BaseToolRunner
from tools.reversing.agent import REVERSING_AGENT_TOOLS
from tools.reversing.manual import REVERSING_MANUAL_TOOLS


class ReversingToolRunner(BaseToolRunner):
    ALLOWED_RUNNERS = {"run_reversing"}

    def run_reversing(self) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}

        for mode in self._resolve_modes():
            results[mode] = self._execute_tool(mode)

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

    def _resolve_modes(self) -> list[str]:
        modes = list(self.context.reversing_tools)
        if "full" in modes:
            return ["info", "imports", "strings"]

        unknown_modes = [mode for mode in modes if mode not in REVERSING_MANUAL_TOOLS]
        if unknown_modes:
            raise ValueError(f"Unknown reversing mode(s): {', '.join(unknown_modes)}")

        return modes

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
