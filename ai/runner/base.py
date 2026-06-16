from abc import ABC, abstractmethod

from core.context import AnalysisContext


class BaseAIRunner(ABC):
    def __init__(self, context: AnalysisContext):
        self.context = context
        self.sample = context.sample


    @abstractmethod
    def run(self):
        pass
