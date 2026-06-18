import json
from typing import Any, Callable

from config import MODEL_PROFILES_PATH
from utils.logger import Logger 
from utils.io.files import load_yaml
from utils.artifacts.builder import JsonBuilder
from core.context import AnalysisContext
from tools.runner.static import StaticToolRunner
from tools.runner.reversing import ReversingToolRunner
from ai.model_registry import ModelRegistry
from ai.runner.static import StaticAgentRunner
from ai.runner.enrichment import EnrichmentAIRunner
from ai.runner.report import ReportAIRunner


class Orchestrator:
    def __init__(self, args: Any):
        self.context = AnalysisContext.from_args(args)
        self.json_builder: JsonBuilder | None = None
        self.static_tools_results: dict[str, Any] = {}
        self.reversing_tools_results: dict[str, Any] = {}
        self.static_tool_runner: StaticToolRunner | None = None
        self.reversing_tool_runner: ReversingToolRunner | None = None
        self._model_registry: ModelRegistry | None = None
        
    
    def _get_phase_handlers(self) -> dict[str, Callable[[], None]]:
        return {
            "static": self.run_static_phase,
            "enrichment": self.run_enrichment_phase,
            "reversing": self.run_reversing_phase,
            "report": self.run_report_phase
        }
    

    def _get_strings_for_static_agent(self) -> list[str]:
        strings = (
            self.static_tools_results
            .get("strings", {})
            .get("data", {})
            .get("parsed_strings", [])
        )

        if isinstance(strings, list):
            return strings

        return []


    def _get_json_builder(self) -> JsonBuilder:
        if self.json_builder is None:
            self.json_builder = JsonBuilder(self.context.output, self.context.sample, self.context.sample_sha256)

        return self.json_builder


    def _get_model_registry(self) -> ModelRegistry:
        if self._model_registry is None:
            profiles = load_yaml("", MODEL_PROFILES_PATH) or {}
            self._model_registry = ModelRegistry(profiles)

        return self._model_registry


    def _get_static_tool_runner(self) -> StaticToolRunner:
        if self.static_tool_runner is None:
            self.static_tool_runner = StaticToolRunner(self.context)

        return self.static_tool_runner


    def _get_reversing_tool_runner(self) -> ReversingToolRunner:
        if self.reversing_tool_runner is None:
            self.reversing_tool_runner = ReversingToolRunner(self.context)
        
        return self.reversing_tool_runner


    def _run_static_agent(self) -> None:
        if not self.context.static_agent:
            return

        strings = self._get_strings_for_static_agent()
        if not strings:
            Logger.warning("No parsed strings found. Skipping static agent.")
            return

        model = self._get_model_registry()
        static_tool_runner = self._get_static_tool_runner()
        static_agent_runner = StaticAgentRunner(self.context, model, strings, static_tool_runner)
        static_agent_runner.run()


    def _run_tools(self, phase_name: str, runner: Any) -> dict[str, Any]:
        Logger.info(f"Executing {phase_name} tools")
        results = runner.run()

        if self.context.output_format == "json":
            self._get_json_builder().save_phase(phase_name, results)

        elif self.context.output_format == "text":
            print(json.dumps(results, indent=4))

        return results


    def _run_static_tools(self) -> None:
        self.static_tools_results = self._run_tools("static", self._get_static_tool_runner())


    def _run_reversing_tools(self) -> None:
        self.reversing_tools_results = self._run_tools("reversing", self._get_reversing_tool_runner())


    def run_static_phase(self) -> None:
        Logger.info("Running static phase")
        self._run_static_tools()
        self._run_static_agent()
        Logger.success("Static phase finished")


    def run_enrichment_phase(self) -> None:
        Logger.info("Running enrichment phase")
        EnrichmentAIRunner(self.context, self._get_model_registry()).run()


    def run_reversing_phase(self) -> None:
        Logger.info("Running reversing phase")
        self._run_reversing_tools()
        Logger.success("Reversing phase finished")


    def run_report_phase(self) -> None:
        Logger.info("Running report phase")
        ReportAIRunner(self.context, self._get_model_registry()).run()


    def run(self) -> None:
        Logger.info(f"Running analysis for: {self.context.sample}")

        handlers = self._get_phase_handlers()
        handler = handlers.get(self.context.phase)
        if handler is None:
            raise ValueError(f"Unknown phase: {self.context.phase}")
        
        handler()

        Logger.success("Analysis finished.")























