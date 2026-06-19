from abc import ABC, abstractmethod
from typing import Any

from orchestrator.context import AnalysisContext


class BaseAIRunner(ABC):
    def __init__(self, context: AnalysisContext) -> None:
        self.context = context


    @abstractmethod
    def run(self) -> Any:
        raise NotImplementedError
