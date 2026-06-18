import json
from typing import Any, Callable

from config import MODEL_PROFILES_PATH, RESULT_FILENAME
from utils.logger import Logger 
from utils.io.files import load_yaml, load_json
from utils.artifacts.extractor import JsonExtractor
from utils.artifacts.builder import JsonBuilder
from core.context import AnalysisContext
from tools.runner.static import StaticToolRunner
from ai.model_registry import ModelRegistry
from ai.runner.static import StaticAgentRunner
from ai.runner.enrichment import EnrichmentAIRunner
from ai.runner.report import ReportAIRunner





class Orchestrator:
    def __init__(self, args: Any):
        self.context = AnalysisContext.from_args(args)
        self.json_builder: JsonBuilder | None = None
        self.static_tools_results: dict[str, Any] = {}
        self.static_tool_runner: StaticToolRunner | None = None
        self._model_registry: ModelRegistry | None = None
        
    
    def _get_phase_handlers(self) -> dict[str, Callable[[], None]]:
        return {
            "static": self.run_static_phase,
            "enrichment": self.run_enrichment_phase,
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


    def _save_static_tools_results(self) -> None:
        if self.context.output_format == "json":
            json_builder = self._get_json_builder()
            json_builder.add_phase("static", self.static_tools_results)
            json_builder.build()

        elif self.context.output_format == "text":
            print(json.dumps(self.static_tools_results, indent=4))


    def _run_static_tools(self) -> None:
        Logger.info("Executing static tools")
        self.static_tools_results = self._get_static_tool_runner().run()



    def run_static_phase(self) -> None:
        Logger.info("Running static phase")
        self._run_static_tools()
        self._save_static_tools_results()
        self._run_static_agent()
        Logger.success("Static phase finished")


    def run_enrichment_phase(self) -> None:
        Logger.info("Running enrichment phase")
        EnrichmentAIRunner(self.context, self._get_model_registry()).run()


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























