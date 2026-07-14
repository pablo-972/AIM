from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from backend.pipeline import run_full_local_pipeline

PHASES = (
    "static",
    "static_inference",
    "dynamic",
    "dynamic_inference",
    "enrichment",
    "reverse_info",
    "reverse_agent",
    "report",
)


PipelineRunner = Callable[
    [
        Path, 
        Path, 
        Callable[[str, str], None], 
        Callable[[dict[str, Any]], None],
    ],
    None,
]


@dataclass
class AnalysisJob:
    analysis_id: str
    filename: str
    sample_path: Path
    output_base: Path
    created_at: str
    status: str = "queued"
    current_phase: str | None = None
    phases: dict[str, str] = field(
        default_factory=lambda: {phase: "pending" for phase in PHASES}
    )
    error: str | None = None
    output_dir: str | None = None
    sample_sha256: str | None = None

    def to_status(self) -> dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "status": self.status,
            "current_phase": self.current_phase,
            "phases": self.phases,
            "error": self.error,
            "filename": self.filename,
            "sample_sha256": self.sample_sha256,
            "output_dir": self.output_dir,
            "created_at": self.created_at,
        }


class AnalysisStore:
    def __init__(
        self,
        pipeline_runner: PipelineRunner = run_full_local_pipeline,
    ) -> None:
        self._jobs: dict[str, AnalysisJob] = {}
        self._lock = Lock()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._pipeline_runner = pipeline_runner

    def create(self, filename: str, sample_path: Path, output_base: Path) -> AnalysisJob:
        analysis_id = output_base.name
        job = AnalysisJob(
            analysis_id=analysis_id,
            filename=filename,
            sample_path=sample_path,
            output_base=output_base,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        with self._lock:
            self._jobs[analysis_id] = job

        self._executor.submit(self._run, analysis_id)
        return job

    def get(self, analysis_id: str) -> AnalysisJob:
        with self._lock:
            job = self._jobs.get(analysis_id)
            if job is None:
                raise KeyError(analysis_id)
            
            return job

    def status(self, analysis_id: str) -> dict[str, Any]:
        return self.get(analysis_id).to_status()

    def list_statuses(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            statuses: dict[str, dict[str, Any]] = {}

            for analysis_id, job in self._jobs.items():
                statuses[analysis_id] = job.to_status()

            return statuses


    def _run(self, analysis_id: str) -> None:
        job = self.get(analysis_id)
        self._set_status(analysis_id, "running")

        try:
            self._pipeline_runner(
                job.sample_path,
                job.output_base,
                lambda phase, state: self._set_phase(analysis_id, phase, state),
                lambda metadata: self._set_metadata(analysis_id, metadata),
            )
        except Exception as exc:
            self._fail(analysis_id, str(exc))
        else:
            self._set_status(analysis_id, "completed", current_phase=None)

    def _set_status(
        self,
        analysis_id: str,
        status: str,
        current_phase: str | None = None,
    ) -> None:
        with self._lock:
            job = self._jobs[analysis_id]
            job.status = status
            job.current_phase = current_phase

    def _set_phase(self, analysis_id: str, phase: str, state: str) -> None:
        with self._lock:
            job = self._jobs[analysis_id]
            job.status = "running"

            if state == "running":
                job.current_phase = phase

            job.phases[phase] = state

            if state in {"completed", "failed"} and job.current_phase == phase:
                job.current_phase = None

    def _set_metadata(self, analysis_id: str, metadata: dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs[analysis_id]
            output_dir = metadata.get("output_dir")
            sample_sha256 = metadata.get("sample_sha256")

            if isinstance(output_dir, str):
                job.output_dir = output_dir

            if isinstance(sample_sha256, str):
                job.sample_sha256 = sample_sha256

    def _fail(self, analysis_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs[analysis_id]
            job.status = "failed"
            job.error = error

            if job.current_phase:
                job.phases[job.current_phase] = "failed"
