from argparse import Namespace
from dataclasses import replace
from pathlib import Path
from typing import Any

from backend.analysis import AnalysisMetadata
from backend.analysis import PipelineObserver, PipelineRunner
from core.orchestrator.orchestrator import Orchestrator
from core.tools.runner.dynamic import DynamicToolRunner
from core.tools.runner.static import StaticToolRunner



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
    observer: PipelineObserver,
) -> None:
    observer.metadata_changed(
        AnalysisMetadata(
            sample_sha256=orchestrator.context.sample_sha256,
            output_dir=str(orchestrator.context.output),
        )
    )


def run_static_tools_phase(
    orchestrator: Orchestrator,
    observer: PipelineObserver,
) -> tuple[Any, dict[str, Any]]:
    static_context = replace(
        orchestrator.context,
        phase="static",
        func="run_static",
        static_tools=["full"],
        static_ai=True,
        profile=orchestrator.context.full_static_profile,
    )

    observer.phase_changed("static", "running")
    static_results = orchestrator._run_tools(
        "static",
        StaticToolRunner(static_context),
        static_context,
        persist_json=True,
    )
    observer.phase_changed("static", "completed")

    return static_context, static_results


def run_static_inference_phase(
    orchestrator: Orchestrator,
    static_context: Any,
    static_results: dict[str, Any],
    observer: PipelineObserver,
) -> None:
    observer.phase_changed("static_inference", "running")
    orchestrator._run_static_strings_inference(static_context, static_results)
    observer.phase_changed("static_inference", "completed")


def run_dynamic_tools_phase(
    orchestrator: Orchestrator,
    observer: PipelineObserver,
) -> tuple[Any, dict[str, Any]]:
    dynamic_context = replace(
        orchestrator.context,
        phase="dynamic",
        func="run_dynamic",
        dynamic_tools=["full"],
        dynamic_ai=True,
        dynamic_start=False,
        dynamic_stop=False,
        profile=orchestrator.context.full_dynamic_profile,
    )

    observer.phase_changed("dynamic", "running")
    dynamic_results = orchestrator._run_tools(
        "dynamic",
        DynamicToolRunner(dynamic_context),
        dynamic_context,
        persist_json=True,
    )
    observer.phase_changed("dynamic", "completed")

    return dynamic_context, dynamic_results


def run_dynamic_inference_phase(
    orchestrator: Orchestrator,
    dynamic_context: Any,
    dynamic_results: dict[str, Any],
    observer: PipelineObserver,
) -> None:
    observer.phase_changed("dynamic_inference", "running")
    orchestrator._run_dynamic_inference(dynamic_context, dynamic_results)
    observer.phase_changed("dynamic_inference", "completed")


def run_enrichment_pipeline_phase(
    orchestrator: Orchestrator,
    observer: PipelineObserver,
) -> None:
    enrichment_context = replace(
        orchestrator.context,
        phase="enrichment",
        func="run_enrichment",
        profile=orchestrator.context.full_enrichment_profile,
    )
    observer.phase_changed("enrichment", "running")
    orchestrator.run_enrichment_phase(enrichment_context)
    observer.phase_changed("enrichment", "completed")


def run_reverse_info_phase(
    orchestrator: Orchestrator,
    observer: PipelineObserver,
) -> None:
    reverse_info_context = replace(
        orchestrator.context,
        phase="reversing",
        func="run_reversing",
        reversing_tools=["full"],
        reversing_agent=False,
        profile=None,
    )
    observer.phase_changed("reverse_info", "running")
    orchestrator.run_reversing_phase(reverse_info_context, persist_json=True)
    observer.phase_changed("reverse_info", "completed")


def run_reverse_agent_phase(
    orchestrator: Orchestrator,
    observer: PipelineObserver,
) -> None:
    reverse_agent_context = replace(
        orchestrator.context,
        phase="reversing",
        func="run_reversing",
        reversing_tools=[],
        reversing_agent=True,
        profile=orchestrator.context.full_reversing_profile,
    )
    observer.phase_changed("reverse_agent", "running")
    orchestrator.run_reversing_phase(reverse_agent_context)
    observer.phase_changed("reverse_agent", "completed")


def run_report_pipeline_phase(
    orchestrator: Orchestrator,
    observer: PipelineObserver,
) -> None:
    report_context = replace(
        orchestrator.context,
        phase="report",
        func="run_report",
        profile=orchestrator.context.full_report_profile,
    )
    observer.phase_changed("report", "running")
    orchestrator.run_report_phase(report_context)
    observer.phase_changed("report", "completed")


def run_full_local_pipeline(
    sample_path: Path,
    output_base: Path,
    observer: PipelineObserver,
) -> None:
    orchestrator = create_full_pipeline_orchestrator(sample_path, output_base)
    emit_pipeline_metadata(orchestrator, observer)

    static_context, static_results = run_static_tools_phase(orchestrator, observer)
    run_static_inference_phase(
        orchestrator, 
        static_context, 
        static_results, 
        observer,
    )

    dynamic_context, dynamic_results = run_dynamic_tools_phase(orchestrator, observer)
    run_dynamic_inference_phase(
        orchestrator, 
        dynamic_context, 
        dynamic_results, 
        observer,
    )

    run_enrichment_pipeline_phase(orchestrator, observer)
    run_reverse_info_phase(orchestrator, observer)
    run_reverse_agent_phase(orchestrator, observer)
    run_report_pipeline_phase(orchestrator, observer)






