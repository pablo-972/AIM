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
            self._jobs[job.sha256] = job

    def get(self, sha256: str) -> AnalysisJob:
        with self._lock:
            job = self._jobs.get(sha256)
            if job is None:
                raise KeyError(sha256)
            
            return job.copy()

    def status(self, sha256: str) -> dict[str, Any]:
        job = self.get(sha256)
        return job.to_status()

    def list_statuses(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            statuses: dict[str, dict[str, Any]] = {}
            for sha256, job in self._jobs.items():
                statuses[sha256] = job.to_status()

            return statuses

    def set_status(
        self,
        sha256: str,
        status: AnalysisStatus,
        current_phase: str | None = None,
    ) -> None:
        with self._lock:
            job = self._get_existing_job(sha256)
            job.status = status.value
            job.current_phase = current_phase

    def set_phase(
        self, 
        sha256: str, 
        phase: str, 
        state: str,
    ) -> None:
        with self._lock:
            job = self._get_existing_job(sha256)
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
        sha256: str, 
        metadata: AnalysisMetadata,
    ) -> None:
        with self._lock:
            job = self._get_existing_job(sha256)

            if metadata.output_dir is not None:
                job.output_dir = metadata.output_dir

    def fail(self, sha256: str, error: str) -> None:
        with self._lock:
            job = self._get_existing_job(sha256)
            job.status = AnalysisStatus.FAILED.value
            job.error = error

            if job.current_phase:
                job.phases[job.current_phase] = PhaseStatus.FAILED.value
                job.current_phase = None


    def _get_existing_job(self, sha256: str) -> AnalysisJob:
        job = self._jobs.get(sha256)
        if job is None:
            raise KeyError(sha256)

        return job
