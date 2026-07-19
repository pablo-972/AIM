from pathlib import Path
from abc import ABC, abstractmethod

from backend.analysis.models import AnalysisMetadata


class PipelineObserver(ABC):
    @abstractmethod
    def phase_changed(self, phase: str, state: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def metadata_changed(self, metadata: AnalysisMetadata) -> None:
        raise NotImplementedError


class PipelineRunner(ABC):
    @abstractmethod
    def run(
        self,
        sample_path: Path,
        output_base: Path,
        observer: PipelineObserver,
    ) -> None:
        raise NotImplementedError
    