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
        sha256: str,
    ) -> None:
        self.repository = repository
        self.sha256 = sha256

    def phase_changed(self, phase: str, state: str) -> None:
        self.repository.set_phase(self.sha256, phase, state)

    def metadata_changed(self, metadata: AnalysisMetadata) -> None:
        self.repository.set_metadata(self.sha256, metadata)


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

        sha256 = output_base.name
        job = AnalysisJob(
            sha256=sha256,
            filename=filename,
            sample_path=sample_path,
            output_base=output_base,
            pipeline_name=pipeline_name,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        self._repository.add(job)
        self._executor.submit(self._run, sha256)

        return job.copy()

    def get(self, sha256: str) -> AnalysisJob:
        return self._repository.get(sha256)

    def status(self, sha256: str) -> dict[str, Any]:
        return self._repository.status(sha256)

    def active_status(self, sha256: str) -> dict[str, Any] | None:
        try:
            status = self._repository.status(sha256)
        except KeyError:
            return None

        if status["status"] in {
            AnalysisStatus.QUEUED.value,
            AnalysisStatus.RUNNING.value,
        }:
            return status

        return None

    def list_statuses(self) -> dict[str, dict[str, Any]]:
        return self._repository.list_statuses()

    def shutdown(self, wait: bool = True) -> None:
        if self._owns_executor:
            self._executor.shutdown(wait=wait)


    def _run(self, sha256: str) -> None:
        job = self._repository.get(sha256)
        observer = AnalysisJobObserver(self._repository, sha256)
        self._repository.set_status(sha256, AnalysisStatus.RUNNING)

        try:
            runner = self._pipeline_registry[job.pipeline_name]
            runner.run(
                job.sample_path,
                job.output_base,
                observer,
                job.filename,
            )
        except Exception as exc:
            self._repository.fail(sha256, str(exc))
            return

        self._repository.set_status(
            sha256,
            AnalysisStatus.COMPLETED,
            current_phase=None,
        )

    def _validate_pipeline_name(self, pipeline_name: str) -> None:
        if pipeline_name in self._pipeline_registry:
            return

        raise KeyError(pipeline_name)
