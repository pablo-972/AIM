from dataclasses import dataclass
from typing import Any, Literal, Protocol


PipelineEventType = Literal[
    "phase_started",
    "phase_completed",
    "phase_failed",
    "metadata_updated",
]


@dataclass(frozen=True)
class PipelineEvent:
    type: PipelineEventType
    phase: str | None = None
    message: str | None = None
    data: dict[str, Any] | None = None


class PipelineEventSink(Protocol):
    def emit(self, event: PipelineEvent) -> None:
        ...


def phase_started(phase: str) -> PipelineEvent:
    return PipelineEvent(type="phase_started", phase=phase)


def phase_completed(phase: str) -> PipelineEvent:
    return PipelineEvent(type="phase_completed", phase=phase)


def phase_failed(phase: str, message: str | None = None) -> PipelineEvent:
    return PipelineEvent(type="phase_failed", phase=phase, message=message)


def metadata_updated(data: dict[str, Any]) -> PipelineEvent:
    return PipelineEvent(type="metadata_updated", data=data)
