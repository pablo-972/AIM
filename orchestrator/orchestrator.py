import json
import argparse
from collections.abc import Callable
from dataclasses import replace
from typing import Any, Protocol

from config import MODEL_PROFILES_PATH
from utils.logger import Logger 
from utils.io.files import load_yaml
from utils.artifacts.builder import JsonBuilder
from utils.artifacts.extractor import get_static_strings_from_tool_results
from orchestrator.context import AnalysisContext
from tools.runner.static import StaticToolRunner
from tools.runner.reversing import ReversingToolRunner
from ai.model_registry import ModelRegistry
from ai.runner.static import StaticInferenceRunner
from ai.runner.reversing import ReversingAgentRunner
from ai.runner.enrichment import EnrichmentAIRunner
from ai.runner.report import ReportAIRunner


class ToolRunner(Protocol):
    def run(self) -> dict[str, Any]:
        ...


class Orchestrator:
    def __init__(self, args: argparse.Namespace) -> None:
        self.context: AnalysisContext = AnalysisContext.from_args(args)
        self.json_builders: dict[str, JsonBuilder] = {}
        self._model_registry: ModelRegistry | None = None
    
    def run(self) -> None:
        Logger.info(f"Running analysis for: {self.context.sample}")

        handlers = self._get_phase_handlers()
        handler = handlers.get(self.context.phase)
        if handler is None:
            raise ValueError(f"Unknown phase: {self.context.phase}")
        
        handler()
        Logger.success("Analysis finished.")

    def run_static_phase(
        self,
        context: AnalysisContext | None = None,
        persist_json: bool = False,
    ) -> None:
        context = context or self.context
        Logger.info("Running static phase")
        results = self._run_static_tools(context, persist_json)
        self._run_static_strings_inference(context, results)
        Logger.success("Static phase finished")


    def run_enrichment_phase(
        self,
        context: AnalysisContext | None = None,
    ) -> None:
        context = context or self.context
        Logger.info("Running enrichment phase")
        EnrichmentAIRunner(context, self._get_model_registry()).run()


    def run_reversing_phase(
        self,
        context: AnalysisContext | None = None,
        persist_json: bool = False,
    ) -> None:
        context = context or self.context
        Logger.info("Running reversing phase")
        if context.reversing_agent:
            self._run_reversing_agent(context)
        else:
            self._run_reversing_tools(context, persist_json)
        Logger.success("Reversing phase finished")


    def run_report_phase(
        self,
        context: AnalysisContext | None = None,
    ) -> None:
        context = context or self.context
        Logger.info("Running report phase")
        ReportAIRunner(context, self._get_model_registry()).run()


    def run_full_phase(self) -> None:
        Logger.info("Running full pipeline")

        static_context = replace(
            self.context,
            phase="static",
            func="run_static",
            static_modes=["full"],
            static_ai=True,
            profile=self.context.full_static_profile,
        )
        self.run_static_phase(static_context, persist_json=True)

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
            reversing_modes=["full"],
            reversing_agent=False,
            profile=None,
        )
        self.run_reversing_phase(
            manual_reversing_context,
            persist_json=True,
        )

        agent_reversing_context = replace(
            self.context,
            phase="reversing",
            func="run_reversing",
            reversing_modes=[],
            reversing_agent=True,
            profile=self.context.full_reversing_profile,
        )
        self.run_reversing_phase(agent_reversing_context)

        Logger.success("Full pipeline finished")
    
    def _get_phase_handlers(self) -> dict[str, Callable[[], None]]:
        return {
            "static": self.run_static_phase,
            "enrichment": self.run_enrichment_phase,
            "reversing": self.run_reversing_phase,
            "report": self.run_report_phase,
            "full": self.run_full_phase,
        }
    
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

    def _run_tools(
        self,
        phase_name: str,
        runner: ToolRunner,
        context: AnalysisContext,
        persist_json: bool = False,
    ) -> dict[str, Any]:
        Logger.info(f"Executing {phase_name} tools")
        results = runner.run()

        if context.output_format == "json" or persist_json:
            self._get_json_builder(context).save_phase(phase_name, results)

        if context.output_format == "text":
            print(json.dumps(results, indent=4))

        return results

    def _run_static_tools(
        self,
        context: AnalysisContext,
        persist_json: bool = False,
    ) -> dict[str, Any]:
        return self._run_tools(
            "static",
            StaticToolRunner(context),
            context,
            persist_json,
        )

    def _run_reversing_tools(
        self,
        context: AnalysisContext,
        persist_json: bool = False,
    ) -> dict[str, Any]:
        return self._run_tools(
            "reversing",
            ReversingToolRunner(context),
            context,
            persist_json,
        )

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

        model = self._get_model_registry()
        static_inference_runner = StaticInferenceRunner(
            context,
            model,
            strings,
        )
        static_inference_runner.run()

    def _run_reversing_agent(self, context: AnalysisContext) -> None:
        if not context.reversing_agent:
            return

        ReversingAgentRunner(
            context,
            self._get_model_registry(),
        ).run()
