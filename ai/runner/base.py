from abc import ABC, abstractmethod
from orchestrator.context import AnalysisContext


class BaseAIRunner(ABC):
    def __init__(self, context: AnalysisContext) -> None:
        self.context: AnalysisContext = context


    @abstractmethod
    def run(self) -> None:
        raise NotImplementedError
