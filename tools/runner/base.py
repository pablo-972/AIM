from abc import ABC

from exceptions import ToolError
from tools.static import is_pe
from core.context import AnalysisContext


class BaseToolRunner(ABC):
    def __init__(self, context: AnalysisContext):
        self.context = context
        self.sample = context.sample
        self.is_pe = is_pe(str(context.sample))
        

    def _selected_runner_name(self) -> str:
        func_name = self.context.func
        if func_name is None:
            raise ToolError("No function selected")
        return func_name


    def _run_selected(self):
        func_name = self._selected_runner_name()
        func = getattr(self, func_name, None)
        if func is None:
            raise ToolError(f"Unknown runner function: {func_name}")
        return func()


    def run(self):
        return self._run_selected()
