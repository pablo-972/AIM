from typing import Any
from threading import Lock

from backend.analysis.models import AnalysisJob, AnalysisMetadata
from backend.analysis.status import AnalysisStatus, PhaseStatus


class AnalysisRepository:
    def __init__(self) -> None:
        self._jobs: dict[str, AnalysisJob] = {}
        self._lock = Lock()

    def add(self, job: AnalysisJob) -> None:
        with self._lock:
            self._jobs[job.analysis_id] = job

    def get(self, analysis_id: str) -> AnalysisJob:
        with self._lock:
            job = self._jobs.get(analysis_id)
            if job is None:
                raise KeyError(analysis_id)
            
            return job.copy()

    def status(self, analysis_id: str) -> dict[str, Any]:
        job = self.get(analysis_id)
        return job.to_status()

    def list_statuses(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            statuses: dict[str, dict[str, Any]] = {}
            for analysis_id, job in self._jobs.items():
                statuses[analysis_id] = job.to_status()

            return statuses

    def set_status(
        self,
        analysis_id: str,
        status: AnalysisStatus,
        current_phase: str | None = None,
    ) -> None:
        with self._lock:
            job = self._get_existing_job(analysis_id)
            job.status = status.value
            job.current_phase = current_phase

    def set_phase(
        self, 
        analysis_id: str, 
        phase: str, 
        state: str,
    ) -> None:
        with self._lock:
            job = self._get_existing_job(analysis_id)
            job.status = AnalysisStatus.RUNNING.value

            if state == PhaseStatus.RUNNING.value:
                job.current_phase = phase

            job.phases[phase] = state

            phase_finished = state in {
                PhaseStatus.COMPLETED.value,
                PhaseStatus.FAILED.value,
            }
            if phase_finished and job.current_phase == phase:
                job.current_phase = None

    def set_metadata(
        self, 
        analysis_id: str, 
        metadata: AnalysisMetadata,
    ) -> None:
        with self._lock:
            job = self._get_existing_job(analysis_id)

            if metadata.output_dir is not None:
                job.output_dir = metadata.output_dir
            if metadata.sample_sha256 is not None:
                job.sample_sha256 = metadata.sample_sha256

    def fail(self, analysis_id: str, error: str) -> None:
        with self._lock:
            job = self._get_existing_job(analysis_id)
            job.status = AnalysisStatus.FAILED.value
            job.error = error

            if job.current_phase:
                job.phases[job.current_phase] = PhaseStatus.FAILED.value
                job.current_phase = None


    def _get_existing_job(self, analysis_id: str) -> AnalysisJob:
        job = self._jobs.get(analysis_id)
        if job is None:
            raise KeyError(analysis_id)

        return job