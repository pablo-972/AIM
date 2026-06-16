import os
import json

from utils.logger import Logger 
from utils.io.files import load_yaml, load_json, save_json
from config import MODEL_PROFILES_PATH, RESULT_FILENAME
from tools.runner.static import StaticToolRunner
from ai.runner.static import StaticAgentRunner
from ai.runner.report import ReportAIRunner
from ai.runner.enrichment import EnrichmentAIRunner
from ai.model_registry import ModelRegistry
from utils.artifacts import (
    append_phase,
    build_analysis_result,
    build_phase,
    get_static_strings,
)
from core.context import AnalysisContext


class Orchestrator:
    PHASE_HANDLERS = {
        "static": "_run_static_phase",
        "report": "_run_report_phase",
        "enrichment": "_run_enrichment_phase",
    }

    def __init__(self, args):
        self.context = AnalysisContext.from_args(args)
        self.sample = self.context.sample
        self.static_tools_results = {}
        self._model_registry = None
        self._static_tool_runner = None


    def _get_model_registry(self) -> ModelRegistry:
        if self._model_registry is None:
            self._model_registry = ModelRegistry(load_yaml("", MODEL_PROFILES_PATH) or {})
        return self._model_registry


    def _get_static_tool_runner(self) -> StaticToolRunner:
        if self._static_tool_runner is None:
            self._static_tool_runner = StaticToolRunner(self.context)
        return self._static_tool_runner


    def _get_strings(self) -> list[str]:
        results = load_json(self.context.output, RESULT_FILENAME) or {}

        parsed_strings = get_static_strings(results)
        if parsed_strings:
            return parsed_strings

        return (
            self.static_tools_results
            .get("strings", {})
            .get("data", {})
            .get("parsed_strings", [])
        )


    def _save_init_result(self):
        init = build_analysis_result(
            sample_path=str(self.sample),
            sample_size=os.path.getsize(self.sample),
        )
        save_json(self.context.output, RESULT_FILENAME, init)


    def _append_phase(self, phase_name: str, phase_data: dict):
        result = load_json(self.context.output, RESULT_FILENAME) or {}
        result = append_phase(result, phase_name, phase_data)
        save_json(self.context.output, RESULT_FILENAME, result)


    def _run_static_tools(self):
        Logger.info("Executing static tools")
        self.static_tools_results = self._get_static_tool_runner().run()


    def _save_static_tools_results(self):
        if self.context.output_format == "json":
            self._save_init_result()
            self._append_phase("static", build_phase(self.static_tools_results))
                
        elif self.context.output_format == "text":
            print(json.dumps(self.static_tools_results, indent=4))


    def _run_static_agent(self):
        if not self.context.static_agent:
            return

        strings = self._get_strings()
        if not strings:
            Logger.warning("No parsed strings found. Skipping static agent.")
            return

        static_agent_runner = StaticAgentRunner(
            self.context,
            self._get_model_registry(),
            strings,
            self._get_static_tool_runner(),
        )
        static_agent_runner.run()


    def _run_static_phase(self):
        self._run_static_tools()
        self._save_static_tools_results()
        self._run_static_agent()


    def _run_report_phase(self):
        ReportAIRunner(self.context, self._get_model_registry()).run()


    def _run_enrichment_phase(self):
        EnrichmentAIRunner(self.context, self._get_model_registry()).run()


    def run(self):
        Logger.info(f"Running analysis for: {self.sample}")

        handler_name = self.PHASE_HANDLERS.get(self.context.phase)
        if handler_name is None:
            raise ValueError(f"Unknown phase: {self.context.phase}")

        getattr(self, handler_name)()
        Logger.success("Analysis finished.")
