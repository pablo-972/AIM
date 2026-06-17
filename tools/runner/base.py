from abc import ABC
from typing import Any

from core.context import AnalysisContext
from exceptions import ToolError



class BaseToolRunner(ABC):
    ALLOWED_RUNNERS: set[str] = set()

    def __init__(self, context: AnalysisContext) -> None:
        self.context = context
        self.sample = context.sample


    def _selected_runner_name(self) -> str:
        func_name = self.context.func
        if not func_name:
            raise ToolError("No runner function selected")
        if func_name not in self.ALLOWED_RUNNERS:
            raise ToolError(f"Runner function not allowed: {func_name}")

        return func_name


    def _run_selected(self) -> Any:
        func_name = self._selected_runner_name()
        func = getattr(self, func_name, None)
        if func is None or not callable(func):
            raise ToolError(f"Unknown runner function: {func_name}")

        return func()


    def run(self) -> Any:
        return self._run_selected()
