from typing import Any
from pathlib import Path
from collections.abc import Mapping
from concurrent.futures import Executor, ThreadPoolExecutor
from datetime import datetime, timezone

from backend.analysis.models import AnalysisJob, AnalysisMetadata
from backend.analysis.repository import AnalysisRepository
from backend.analysis.pipeline import PipelineRunner, PipelineObserver
from backend.analysis.status import AnalysisStatus


class AnalysisJobObserver(PipelineObserver):
    def __init__(
        self, 
        repository: AnalysisRepository, 
        analysis_id: str,
    ) -> None:
        self.repository = repository
        self.analysis_id = analysis_id

    def phase_changed(self, phase: str, state: str) -> None:
        self.repository.set_phase(self.analysis_id, phase, state)

    def metadata_changed(self, metadata: AnalysisMetadata) -> None:
        self.repository.set_metadata(self.analysis_id, metadata)


class AnalysisService:
    def __init__(
        self,
        pipeline_registry: Mapping[str, PipelineRunner],
        repository: AnalysisRepository | None = None,
        executor: Executor | None = None,
    ) -> None:
        self._pipeline_registry = dict(pipeline_registry)
        self._repository = repository or AnalysisRepository()

        if executor is None:
            self._executor: Executor = ThreadPoolExecutor(max_workers=1)
            self._owns_executor = True
        else:
            self._executor = executor
            self._owns_executor = False

    def create(
        self,
        filename: str,
        sample_path: Path,
        output_base: Path,
        pipeline_name: str,
    ) -> AnalysisJob:
        self._validate_pipeline_name(pipeline_name)

        analysis_id = output_base.name
        job = AnalysisJob(
            analysis_id=analysis_id,
            filename=filename,
            sample_path=sample_path,
            output_base=output_base,
            pipeline_name=pipeline_name,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        self._repository.add(job)
        self._executor.submit(self._run, analysis_id)

        return job.copy()

    def get(self, analysis_id: str) -> AnalysisJob:
        return self._repository.get(analysis_id)

    def status(self, analysis_id: str) -> dict[str, Any]:
        return self._repository.status(analysis_id)

    def list_statuses(self) -> dict[str, dict[str, Any]]:
        return self._repository.list_statuses()

    def shutdown(self, wait: bool = True) -> None:
        if self._owns_executor:
            self._executor.shutdown(wait=wait)


    def _run(self, analysis_id: str) -> None:
        job = self._repository.get(analysis_id)
        observer = AnalysisJobObserver(self._repository, analysis_id)
        self._repository.set_status(analysis_id, AnalysisStatus.RUNNING)

        try:
            runner = self._pipeline_registry[job.pipeline_name]
            runner.run(job.sample_path, job.output_base, observer)
        except Exception as exc:
            self._repository.fail(analysis_id, str(exc))
            return

        self._repository.set_status(
            analysis_id,
            AnalysisStatus.COMPLETED,
            current_phase=None,
        )

    def _validate_pipeline_name(self, pipeline_name: str) -> None:
        if pipeline_name in self._pipeline_registry:
            return

        raise KeyError(pipeline_name)