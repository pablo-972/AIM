from abc import ABC
from pathlib import Path
from typing import Any, cast

from exceptions import ToolError
from orchestrator.context import AnalysisContext



class BaseToolRunner(ABC):
    ALLOWED_RUNNERS: set[str] = set()


    def __init__(self, context: AnalysisContext) -> None:
        self.context: AnalysisContext = context
        self.sample: Path = context.sample


    def _selected_runner_name(self) -> str:
        func_name = self.context.func
        
        if not func_name:
            raise ToolError("No runner function selected")
        
        if func_name not in self.ALLOWED_RUNNERS:
            raise ToolError(f"Runner function not allowed: {func_name}")

        return func_name


    def run(self) -> dict[str, Any]:
        func_name = self._selected_runner_name()
        func = getattr(self, func_name, None)

        if func is None or not callable(func):
            raise ToolError(f"Unknown runner function: {func_name}")

        result = func()
        if not isinstance(result, dict):
            raise ToolError(f"Runner function returned a non-object result: {func_name}")

        return cast(dict[str, Any], result)
