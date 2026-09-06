import json
import argparse
from typing import Any, Protocol

from config import MODEL_PROFILES_PATH
from core.utils.logger import Logger 
from core.utils.io.files import load_yaml
from core.utils.artifacts.builder import JsonBuilder
from core.utils.artifacts.extractor import get_static_strings_from_tool_results
from core.orchestrator.context import AnalysisContext
from core.orchestrator.event import (
    PipelineEventSink,
    phase_completed,
    phase_started,
)
from core.tools.runner.static import StaticToolRunner
from core.tools.runner.dynamic import DynamicToolRunner
from core.tools.runner.reversing import ReversingToolRunner
from core.ai.model_registry import ModelRegistry
from core.ai.runner.static import StaticInferenceRunner
from core.ai.runner.dynamic import DynamicInferenceRunner
from core.ai.runner.reversing import ReversingAgentRunner
from core.ai.runner.enrichment import EnrichmentAIRunner
from core.ai.runner.report import ReportAIRunner


class ToolRunner(Protocol):
    def run(self) -> dict[str, Any]:
        ...


class Orchestrator:
    def __init__(self, args: argparse.Namespace) -> None:
        self.context: AnalysisContext = AnalysisContext.from_args(args)
        self._json_builders: dict[str, JsonBuilder] = {}
        self._model_registry: ModelRegistry | None = None

    def run(self) -> None:
        Logger.info(f"Running analysis for: {self.context.sample}")

        match self.context.phase:
            case "static":
                self.run_static_phase(self.context)
            case "dynamic":
                self.run_dynamic_phase(self.context)
            case "enrichment":
                self.run_enrichment_phase(self.context)
            case "reversing":
                self.run_reversing_phase(self.context)
            case "report":
                self.run_report_phase(self.context)
            case "full":
                self.run_full_phase(self.context)
            case _:
                raise ValueError(f"Unknown phase: {self.context.phase}")

        Logger.success("Analysis finished.")

    def run_static_phase(
        self,
        context: AnalysisContext,
        persist_json: bool = False,
        event_sink: PipelineEventSink | None = None,
    ) -> None:
        Logger.info("Running static phase")

        self._emit_phase_started(
            event_sink,
            "static",
        )
        results = self._run_tools(
            "static",
            StaticToolRunner(context),
            context,
            persist_json=persist_json,
        )
        self._emit_phase_completed(
            event_sink,
            "static",
        )

        if context.static.ai:
            self._emit_phase_started(event_sink, "static_inference")
            self._run_static_inference(context, results)
            self._emit_phase_completed(event_sink, "static_inference")
        
        Logger.success("Static phase finished")

    def run_dynamic_phase(
        self,
        context: AnalysisContext,
        persist_json: bool = False,
        event_sink: PipelineEventSink | None = None,
    ) -> None:
        Logger.info("Running dynamic phase")

        self._emit_phase_started(
            event_sink,
            "dynamic",
        )
        results = self._run_tools(
            "dynamic",
            DynamicToolRunner(context),
            context,
            persist_json=persist_json,
        )
        self._emit_phase_completed(
            event_sink,
            "dynamic",
        )

        if context.dynamic.ai:
            self._emit_phase_started(event_sink, "dynamic_inference")
            self._run_dynamic_inference(context, results)
            self._emit_phase_completed(event_sink, "dynamic_inference")

        Logger.success("Dynamic phase finished")

    def run_enrichment_phase(
        self,
        context: AnalysisContext,
        event_sink: PipelineEventSink | None = None,
        event_phase: str = "enrichment",
    ) -> None:
        Logger.info("Running enrichment phase")

        self._emit_phase_started(event_sink, event_phase)
        enrichment_runner = EnrichmentAIRunner(context, self._get_model_registry())
        enrichment_runner.run()
        self._emit_phase_completed(event_sink, event_phase)

        Logger.success("Enrichment phase finished")

    def run_reversing_phase(
        self,
        context: AnalysisContext,
        persist_json: bool = False,
        event_sink: PipelineEventSink | None = None,
        event_phase: str = "reversing",
    ) -> None:
        Logger.info("Running reversing phase")

        self._emit_phase_started(
            event_sink,
            event_phase,
        )
        if context.reversing.agent:
            self._run_reversing_agent(context)
        else:
            self._run_tools(
                "reversing",
                ReversingToolRunner(context),
                context,
                persist_json=persist_json,
            )
        self._emit_phase_completed(
            event_sink,
            event_phase,
        )

        Logger.success("Reversing phase finished")

    def run_report_phase(
        self,
        context: AnalysisContext,
        event_sink: PipelineEventSink | None = None,
        event_phase: str = "report",
    ) -> None:
        Logger.info("Running report phase")

        self._emit_phase_started(event_sink, event_phase)
        report_runner = ReportAIRunner(context, self._get_model_registry())
        report_runner.run()
        self._emit_phase_completed(event_sink, event_phase)

        Logger.success("Report phase finished")

    def run_full_phase(
        self,
        context: AnalysisContext,
        event_sink: PipelineEventSink | None = None,
    ) -> None:
        Logger.info("Running full pipeline")
        self.run_full_static_phase(context, event_sink=event_sink)
        self.run_full_dynamic_phase(context, event_sink=event_sink)
        self.run_full_enrichment_phase(context, event_sink=event_sink)
        self.run_full_reverse_info_phase(context, event_sink=event_sink)
        self.run_full_reverse_agent_phase(context, event_sink=event_sink)
        self.run_full_report_phase(context, event_sink=event_sink)

        Logger.success("Full pipeline finished")

    def run_full_static_phase(
        self,
        context: AnalysisContext,
        event_sink: PipelineEventSink | None = None,
    ) -> None:
        static_context = context.for_full_static()
        self.run_static_phase(
            static_context,
            persist_json=True,
            event_sink=event_sink,
        )

    def run_full_dynamic_phase(
        self,
        context: AnalysisContext,
        event_sink: PipelineEventSink | None = None,
    ) -> None:
        dynamic_context = context.for_full_dynamic()
        self.run_dynamic_phase(
            dynamic_context,
            persist_json=True,
            event_sink=event_sink,
        )

    def run_full_enrichment_phase(
        self,
        context: AnalysisContext,
        event_sink: PipelineEventSink | None = None,
    ) -> None:
        enrichment_context = context.for_full_enrichment()
        self.run_enrichment_phase(
            enrichment_context,
            event_sink=event_sink,
        )

    def run_full_reverse_info_phase(
        self,
        context: AnalysisContext,
        event_sink: PipelineEventSink | None = None,
    ) -> None:
        manual_reversing_context = context.for_full_reverse_info()
        self.run_reversing_phase(
            manual_reversing_context,
            persist_json=True,
            event_sink=event_sink,
            event_phase="reverse_info",
        )

    def run_full_reverse_agent_phase(
        self,
        context: AnalysisContext,
        event_sink: PipelineEventSink | None = None,
    ) -> None:
        agent_reversing_context = context.for_full_reverse_agent()
        self.run_reversing_phase(
            agent_reversing_context,
            event_sink=event_sink,
            event_phase="reverse_agent",
        )

    def run_full_report_phase(
        self,
        context: AnalysisContext,
        event_sink: PipelineEventSink | None = None,
    ) -> None:
        report_context = context.for_full_report()
        self.run_report_phase(
            report_context,
            event_sink=event_sink,
        )


    def _run_tools(
        self,
        phase_name: str,
        runner: ToolRunner,
        context: AnalysisContext,
        persist_json: bool = False,
    ) -> dict[str, Any]:
        Logger.info(f"Executing {phase_name} tools")
        results = runner.run()
        save_json = context.output_format == "json" or persist_json
        print_text = context.output_format == "text"

        if save_json:
            json_builder = self._get_json_builder(context)
            json_builder.save_phase(phase_name, results)
        elif print_text:
            print(json.dumps(results, indent=4))

        Logger.success("Tools executed successfully")
        return results

    def _run_static_inference(
        self,
        context: AnalysisContext,
        results: dict[str, Any],
    ) -> None:
        if not context.static.ai:
            return

        strings = get_static_strings_from_tool_results(results)
        if not strings:
            Logger.warning("No parsed strings found. Skipping static AI inference.")
            return

        Logger.info("Running static AI inference")
        model = self._get_model_registry()
        static_inference_runner = StaticInferenceRunner(context, model, strings)
        static_inference_runner.run()

        Logger.success("Static AI inference finished")

    def _run_dynamic_inference(
        self,
        context: AnalysisContext,
        results: dict[str, Any],
    ) -> None:
        if not context.dynamic.ai:
            return

        Logger.info("Running dynamic AI inference")
        model = self._get_model_registry()
        dynamic_inference_runner = DynamicInferenceRunner(context, model, results)
        dynamic_inference_runner.run()

        Logger.success("Dynamic AI inference finished")

    def _run_reversing_agent(self, context: AnalysisContext) -> None:
        if not context.reversing.agent:
            return

        Logger.info("Running AI reversing agent")
        model = self._get_model_registry()
        rev_agent_runner = ReversingAgentRunner(context, model)
        rev_agent_runner.run()

        Logger.success("Reversing agent finished")


    def _get_json_builder(self, context: AnalysisContext) -> JsonBuilder:
        output_key = str(context.output)
        builder = self._json_builders.get(output_key)

        if builder is None:
            builder = JsonBuilder(
                context.output,
                context.sample,
                context.sample_sha256,
                context.sample_filename,
            )
            self._json_builders[output_key] = builder

        return builder

    def _get_model_registry(self) -> ModelRegistry:
        if self._model_registry is None:
            profiles = load_yaml("", MODEL_PROFILES_PATH) or {}
            self._model_registry = ModelRegistry(profiles)

        return self._model_registry

    def _emit_phase_started(
        self,
        event_sink: PipelineEventSink | None,
        phase: str,
    ) -> None:
        if event_sink is None:
            return
        event_sink.emit(phase_started(phase))

    def _emit_phase_completed(
        self,
        event_sink: PipelineEventSink | None,
        phase: str,
    ) -> None:
        if event_sink is None:
            return
        event_sink.emit(phase_completed(phase))
