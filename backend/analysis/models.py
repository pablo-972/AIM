from __future__ import annotations

from typing import Any
from pathlib import Path
from dataclasses import dataclass, field

from backend.analysis.status import AnalysisStatus, PhaseStatus


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


@dataclass
class AnalysisMetadata:
    output_dir: str | None = None


def create_phases() -> dict[str, str]:
    phases = {}
    for phase in PHASES:
        phases[phase] = PhaseStatus.PENDING.value

    return phases


@dataclass
class AnalysisJob:
    sha256: str
    filename: str
    sample_path: Path
    output_base: Path
    pipeline_name: str
    created_at: str
    status: str = AnalysisStatus.QUEUED.value
    current_phase: str | None = None
    phases: dict[str, str] = field(default_factory=create_phases)
    error: str | None = None
    output_dir: str | None = None

    def to_status(self) -> dict[str, Any]:
        return {
            "sha256": self.sha256,
            "status": self.status,
            "current_phase": self.current_phase,
            "phases": dict(self.phases),
            "error": self.error,
            "filename": self.filename,
            "pipeline_name": self.pipeline_name,
            "output_dir": self.output_dir,
            "created_at": self.created_at,
        }

    def copy(self) -> AnalysisJob:
        return AnalysisJob(
            sha256=self.sha256,
            filename=self.filename,
            sample_path=self.sample_path,
            output_base=self.output_base,
            pipeline_name=self.pipeline_name,
            created_at=self.created_at,
            status=self.status,
            current_phase=self.current_phase,
            phases=dict(self.phases),
            error=self.error,
            output_dir=self.output_dir,
        )
