import json
import argparse
from dataclasses import replace
from typing import Any, Protocol

from config import MODEL_PROFILES_PATH
from core.utils.logger import Logger 
from core.utils.io.files import load_yaml
from core.utils.artifacts.builder import JsonBuilder
from core.utils.artifacts.extractor import get_static_strings_from_tool_results
from core.orchestrator.context import AnalysisContext
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
    PHASE_HANDLERS: dict[str,str] = {
        "static": "run_static_phase",
        "dynamic": "run_dynamic_phase",
        "enrichment": "run_enrichment_phase",
        "reversing": "run_reversing_phase",
        "report": "run_report_phase",
        "full": "run_full_phase",
    }

    def __init__(self, args: argparse.Namespace) -> None:
        self.context: AnalysisContext = AnalysisContext.from_args(args)
        self.json_builders: dict[str, JsonBuilder] = {}
        self._model_registry: ModelRegistry | None = None

    def run(self) -> None:
        Logger.info(f"Running analysis for: {self.context.sample}")

        handler = self.PHASE_HANDLERS.get(self.context.phase)
        if handler is None:
            raise ValueError(f"Unknown phase: {self.context.phase}")
        
        getattr(self, handler)()

        Logger.success("Analysis finished.")

    def run_static_phase(
        self,
        context: AnalysisContext | None = None,
        persist_json: bool = False,
    ) -> None:
        Logger.info("Running static phase")

        context = context or self.context

        results = self._run_tools(
            "static",
            StaticToolRunner(context),
            context,
            persist_json,
        )
        self._run_static_strings_inference(context, results)
        
        Logger.success("Static phase finished")

    def run_dynamic_phase(
        self,
        context: AnalysisContext | None = None,
        persist_json: bool = False,
    ) -> None:
        Logger.info("Running dynamic phase")

        context = context or self.context

        results = self._run_tools(
            "dynamic",
            DynamicToolRunner(context),
            context,
            persist_json,
        )
        self._run_dynamic_inference(context, results)

        Logger.success("Dynamic phase finished")

    def run_enrichment_phase(self, context: AnalysisContext | None = None) -> None:
        Logger.info("Running enrichment phase")
        
        context = context or self.context

        enrichment_runner = EnrichmentAIRunner(context, self._get_model_registry())
        enrichment_runner.run()

    def run_reversing_phase(
        self,
        context: AnalysisContext | None = None,
        persist_json: bool = False,
    ) -> None:
        Logger.info("Running reversing phase")

        context = context or self.context

        if context.reversing_agent:
            self._run_reversing_agent(context)
        else:
            self._run_tools(
                "reversing",
                ReversingToolRunner(context),
                context,
                persist_json,
            )

        Logger.success("Reversing phase finished")

    def run_report_phase(
        self,
        context: AnalysisContext | None = None,
    ) -> None:
        Logger.info("Running report phase")

        context = context or self.context
        
        report_runner = ReportAIRunner(context, self._get_model_registry())
        report_runner.run()

        Logger.success("Report phase finished")

    def run_full_phase(self) -> None:
        Logger.info("Running full pipeline")

        static_context = replace(
            self.context,
            phase="static",
            func="run_static",
            static_tools=["full"],
            static_ai=True,
            profile=self.context.full_static_profile,
        )
        self.run_static_phase(static_context, persist_json=True)

        dynamic_context = replace(
            self.context,
            phase="dynamic",
            func="run_dynamic",
            dynamic_tools=["full"],
            dynamic_ai=True,
            dynamic_start=False,
            dynamic_stop=False,
            profile=self.context.full_dynamic_profile,
        )
        self.run_dynamic_phase(dynamic_context, persist_json=True)

        enrichment_context = replace(
            self.context,
            phase="enrichment",
            func="run_enrichment",
            profile=self.context.full_enrichment_profile,
        )
        self.run_enrichment_phase(enrichment_context)

        manual_reversing_context = replace(
            self.context,
            phase="reversing",
            func="run_reversing",
            reversing_tools=["full"],
            reversing_agent=False,
            profile=None,
        )
        self.run_reversing_phase(manual_reversing_context, persist_json=True)

        agent_reversing_context = replace(
            self.context,
            phase="reversing",
            func="run_reversing",
            reversing_tools=[],
            reversing_agent=True,
            profile=self.context.full_reversing_profile,
        )
        self.run_reversing_phase(agent_reversing_context)

        report_context = replace(
            self.context,
            phase="report",
            func="run_report",
            profile=None,
        )
        self.run_report_phase(report_context)

        Logger.success("Full pipeline finished")
    

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

    def _run_static_strings_inference(
        self,
        context: AnalysisContext,
        results: dict[str, Any],
    ) -> None:
        if not context.static_ai:
            return

        strings = get_static_strings_from_tool_results(results)
        if not strings:
            Logger.warning("No parsed strings found. Skipping static AI inference.")
            return

        Logger.info("Running static strings AI inference")

        model = self._get_model_registry()
        static_inference_runner = StaticInferenceRunner(context, model, strings)
        static_inference_runner.run()

        Logger.success("Static strings AI inference finished")

    def _run_dynamic_inference(
        self,
        context: AnalysisContext,
        results: dict[str, Any],
    ) -> None:
        if not context.dynamic_ai:
            return

        Logger.info("Running dynamic AI inference")

        model = self._get_model_registry()
        dynamic_inference_runner = DynamicInferenceRunner(context, model, results)
        dynamic_inference_runner.run()

        Logger.success("Dynamic AI inference finished")

    def _run_reversing_agent(self, context: AnalysisContext) -> None:
        if not context.reversing_agent:
            return

        Logger.info("Running AI reversing agent")

        model = self._get_model_registry()
        rev_agent_runner = ReversingAgentRunner(context, model)
        rev_agent_runner.run()

        Logger.success("Reversing agent finished")


    def _get_json_builder(self, context: AnalysisContext) -> JsonBuilder:
        output_key = str(context.output)
        builder = self.json_builders.get(output_key)

        if builder is None:
            builder = JsonBuilder(
                context.output,
                context.sample,
                context.sample_sha256,
            )
            self.json_builders[output_key] = builder

        return builder

    def _get_model_registry(self) -> ModelRegistry:
        if self._model_registry is None:
            profiles = load_yaml("", MODEL_PROFILES_PATH) or {}
            self._model_registry = ModelRegistry(profiles)

        return self._model_registry
