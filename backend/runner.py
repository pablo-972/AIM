from argparse import Namespace
from pathlib import Path

from backend.analysis import AnalysisMetadata
from backend.analysis import PipelineObserver, PipelineRunner
from core.orchestrator.event import (
    PipelineEvent,
    PipelineEventSink,
    metadata_updated,
)
from core.orchestrator.orchestrator import Orchestrator


class LocalPipelineRunner(PipelineRunner):
    def run(
        self,
        sample_path: Path,
        output_base: Path,
        observer: PipelineObserver,
    ) -> None:
        run_full_local_pipeline(sample_path, output_base, observer)


DEFAULT_PIPELINE_NAME = "full"
PIPELINE_RUNNERS = {
    DEFAULT_PIPELINE_NAME: LocalPipelineRunner(),
}


class BackendPipelineEventSink(PipelineEventSink):
    def __init__(self, observer: PipelineObserver) -> None:
        self.observer = observer

    def emit(self, event: PipelineEvent) -> None:
        if event.type == "phase_started" and event.phase:
            self.observer.phase_changed(event.phase, "running")
            return

        if event.type == "phase_completed" and event.phase:
            self.observer.phase_changed(event.phase, "completed")
            return

        if event.type == "phase_failed" and event.phase:
            self.observer.phase_changed(event.phase, "failed")
            return

        if event.type == "metadata_updated" and event.data:
            self.observer.metadata_changed(
                AnalysisMetadata(
                    sample_sha256=_optional_string(event.data.get("sample_sha256")),
                    output_dir=_optional_string(event.data.get("output_dir")),
                )
            )


def create_full_pipeline_orchestrator(
    sample_path: Path,
    output_base: Path,
) -> Orchestrator:
    args = Namespace(
        sample=str(sample_path),
        output=str(output_base.parent),
        format="json",
        phase="full",
        func="run_full",
        static_profile="local-static",
        dynamic_profile="local-dynamic",
        enrichment_profile="local-enrichment",
        reversing_profile="local-reversing",
        reversing_max_targets=12,
        report_profile="gemini-report",
    )

    return Orchestrator(args)


def emit_pipeline_metadata(
    orchestrator: Orchestrator,
    event_sink: PipelineEventSink,
) -> None:
    event_sink.emit(
        metadata_updated(
            {
                "sample_sha256": orchestrator.context.sample_sha256,
                "output_dir": str(orchestrator.context.output),
            }
        )
    )


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def run_full_local_pipeline(
    sample_path: Path,
    output_base: Path,
    observer: PipelineObserver,
) -> None:
    orchestrator = create_full_pipeline_orchestrator(sample_path, output_base)
    event_sink = BackendPipelineEventSink(observer)
    emit_pipeline_metadata(orchestrator, event_sink)

    orchestrator.run_full_static_phase(event_sink)
    orchestrator.run_full_dynamic_phase(event_sink)
    orchestrator.run_full_enrichment_phase(event_sink)
    orchestrator.run_full_reverse_info_phase(event_sink)
    orchestrator.run_full_reverse_agent_phase(event_sink)
    orchestrator.run_full_report_phase(event_sink)
