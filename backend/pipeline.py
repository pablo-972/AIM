from argparse import Namespace
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

from core.orchestrator.orchestrator import Orchestrator
from core.tools.runner.dynamic import DynamicToolRunner
from core.tools.runner.static import StaticToolRunner

PhaseCallback = Callable[[str, str], None]
MetadataCallback = Callable[[dict[str, Any]], None]


def noop_phase_callback(_phase: str, _state: str) -> None:
    return None


def noop_metadata_callback(_metadata: dict[str, Any]) -> None:
    return None


def create_full_pipeline_orchestrator(
    sample_path: Path, 
    output_base: Path,
) -> Orchestrator:
    args = Namespace(
        sample=str(sample_path),
        output=str(output_base),
        format="json",
        phase="full",
        func="run_full",
        static_profile="local-static",
        dynamic_profile="local-dynamic",
        enrichment_profile="local-enrichment",
        reversing_profile="local-reversing",
        reversing_max_targets=12,
    )

    return Orchestrator(args)


def emit_pipeline_metadata(
    orchestrator: Orchestrator,
    on_metadata: MetadataCallback = noop_metadata_callback,
) -> None:
    on_metadata(
        {
            "sample_sha256": orchestrator.context.sample_sha256,
            "output_dir": str(orchestrator.context.output),
        }
    )


def run_static_tools_phase(
    orchestrator: Orchestrator,
    on_phase: PhaseCallback = noop_phase_callback,
) -> tuple[Any, dict[str, Any]]:
    static_context = replace(
        orchestrator.context,
        phase="static",
        func="run_static",
        static_tools=["full"],
        static_ai=True,
        profile=orchestrator.context.full_static_profile,
    )

    on_phase("static", "running")
    static_results = orchestrator._run_tools(
        "static",
        StaticToolRunner(static_context),
        static_context,
        persist_json=True,
    )
    on_phase("static", "completed")

    return static_context, static_results


def run_static_inference_phase(
    orchestrator: Orchestrator,
    static_context: Any,
    static_results: dict[str, Any],
    on_phase: PhaseCallback = noop_phase_callback,
) -> None:
    on_phase("static_inference", "running")
    orchestrator._run_static_strings_inference(static_context, static_results)
    on_phase("static_inference", "completed")


def run_dynamic_tools_phase(
    orchestrator: Orchestrator,
    on_phase: PhaseCallback = noop_phase_callback,
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

    on_phase("dynamic", "running")
    dynamic_results = orchestrator._run_tools(
        "dynamic",
        DynamicToolRunner(dynamic_context),
        dynamic_context,
        persist_json=True,
    )
    on_phase("dynamic", "completed")

    return dynamic_context, dynamic_results


def run_dynamic_inference_phase(
    orchestrator: Orchestrator,
    dynamic_context: Any,
    dynamic_results: dict[str, Any],
    on_phase: PhaseCallback = noop_phase_callback,
) -> None:
    on_phase("dynamic_inference", "running")
    orchestrator._run_dynamic_inference(dynamic_context, dynamic_results)
    on_phase("dynamic_inference", "completed")


def run_enrichment_pipeline_phase(
    orchestrator: Orchestrator,
    on_phase: PhaseCallback = noop_phase_callback,
) -> None:
    enrichment_context = replace(
        orchestrator.context,
        phase="enrichment",
        func="run_enrichment",
        profile=orchestrator.context.full_enrichment_profile,
    )
    on_phase("enrichment", "running")
    orchestrator.run_enrichment_phase(enrichment_context)
    on_phase("enrichment", "completed")


def run_reverse_info_phase(
    orchestrator: Orchestrator,
    on_phase: PhaseCallback = noop_phase_callback,
) -> None:
    reverse_info_context = replace(
        orchestrator.context,
        phase="reversing",
        func="run_reversing",
        reversing_tools=["full"],
        reversing_agent=False,
        profile=None,
    )
    on_phase("reverse_info", "running")
    orchestrator.run_reversing_phase(reverse_info_context, persist_json=True)
    on_phase("reverse_info", "completed")


def run_reverse_agent_phase(
    orchestrator: Orchestrator,
    on_phase: PhaseCallback = noop_phase_callback,
) -> None:
    reverse_agent_context = replace(
        orchestrator.context,
        phase="reversing",
        func="run_reversing",
        reversing_tools=[],
        reversing_agent=True,
        profile=orchestrator.context.full_reversing_profile,
    )
    on_phase("reverse_agent", "running")
    orchestrator.run_reversing_phase(reverse_agent_context)
    on_phase("reverse_agent", "completed")


def run_report_pipeline_phase(
    orchestrator: Orchestrator,
    on_phase: PhaseCallback = noop_phase_callback,
) -> None:
    report_context = replace(
        orchestrator.context,
        phase="report",
        func="run_report",
        profile=None,
    )
    on_phase("report", "running")
    orchestrator.run_report_phase(report_context)
    on_phase("report", "completed")


def run_full_local_pipeline(
    sample_path: Path,
    output_base: Path,
    on_phase: PhaseCallback,
    on_metadata: MetadataCallback,
) -> None:
    """Run the fixed local full pipeline used by the web UI."""
    orchestrator = create_full_pipeline_orchestrator(sample_path, output_base)
    emit_pipeline_metadata(orchestrator, on_metadata)

    static_context, static_results = run_static_tools_phase(orchestrator, on_phase)
    run_static_inference_phase(orchestrator, static_context, static_results, on_phase)

    dynamic_context, dynamic_results = run_dynamic_tools_phase(orchestrator, on_phase)
    run_dynamic_inference_phase(orchestrator, dynamic_context, dynamic_results, on_phase)

    run_enrichment_pipeline_phase(orchestrator, on_phase)
    run_reverse_info_phase(orchestrator, on_phase)
    run_reverse_agent_phase(orchestrator, on_phase)
    run_report_pipeline_phase(orchestrator, on_phase)
