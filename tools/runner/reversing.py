from typing import Any
from collections.abc import Callable

from utils.logger import Logger
from core.results import ToolResult
from tools.runner.base import BaseToolRunner
from tools.reversing import (
    run_info,
    run_imports,
    run_functions,
    run_reversing_strings,
    run_disasm,
    run_xrefs,
    run_string_xrefs,
)


ReverseTool = Callable[..., dict[str, Any] | list[dict[str, Any]]]


REVERSING_TOOL_RUNNERS: dict[str, ReverseTool] = {
    "info": run_info,
    "imports": run_imports,
    "functions": run_functions,
    "strings": run_reversing_strings,
    "disasm": run_disasm,
    "xrefs": run_xrefs,
    "string-xrefs": run_string_xrefs,
}


class ReversingToolRunner(BaseToolRunner):
    ALLOWED_RUNNERS = {"run_reversing"}

    def __init__(self, context: Any) -> None:
        super().__init__(context)


    def _resolve_modes(self) -> list[str]:
        modes = list(getattr(self.context, "reversing_modes", []) or [])
        unknown_modes = [mode for mode in modes if mode not in REVERSING_TOOL_RUNNERS]

        if unknown_modes:
            raise ValueError(f"Unknown reverse mode(s): {', '.join(unknown_modes)}")

        return modes


    def _build_tool_kwargs(self, mode: str) -> dict[str, Any]:
        if mode == "disasm":
            return {"function": getattr(self.context, "function", None)}

        if mode == "xrefs":
            return {"value": getattr(self.context, "value", None)}

        if mode == "string-xrefs":
            return {"string_value": getattr(self.context, "value", None)}

        return {}


    def _execute_tool(self, mode: str) -> dict[str, Any]:
        Logger.info(f"Executing reverse tool: {mode}")
        tool = REVERSING_TOOL_RUNNERS[mode]

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