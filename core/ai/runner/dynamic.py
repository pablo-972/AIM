import json
from typing import Any

from config import DYNAMIC_INFERENCE_RESULT_FILENAME
from core.utils.logger import Logger
from core.utils.preprocessing.dynamic.inference import prepare_dynamic_inference_inputs
from core.ai.inferences.dynamic import DynamicInference
from core.ai.runtime.memory import TraceMemory
from core.ai.runner.base import BaseAIRunner
from core.ai.model_registry import ModelRegistry
from core.orchestrator.context import AnalysisContext


class DynamicInferenceRunner(BaseAIRunner):
    def __init__(
        self,
        context: AnalysisContext,
        model_registry: ModelRegistry,
        dynamic_results: dict[str, Any],
    ) -> None:
        super().__init__(context)

        self.model_registry = model_registry
        self.dynamic_results = dynamic_results

    def run(self) -> None:
        inputs = prepare_dynamic_inference_inputs(self.dynamic_results)
        if not inputs:
            Logger.warning("No dynamic evidence found. Skipping dynamic AI inference.")
            return

        inference = self._create_inference_model()
        memory = TraceMemory(
            output_dir=self.context.output,
            filename=DYNAMIC_INFERENCE_RESULT_FILENAME,
            agent_name="dynamic_inference",
        )

        try:
            for input_ref in inputs:
                self._process_input(inference, memory, input_ref)
        except Exception as exc:
            memory.fail(str(exc))
            raise
        else:
            memory.close()


    def _process_input(
        self,
        inference: DynamicInference,
        memory: TraceMemory,
        input_ref: dict[str, Any],
    ) -> None:
        existing_explanations = self._existing_explanations(memory)

        try:
            decision = inference.analyze_section(input_ref, existing_explanations)
        except Exception as exc:
            error = self._error_message(input_ref, exc)
            Logger.error(error)

            memory.record(
                decision=self._failed_decision(),
                input_ref=self._compact_input_ref(input_ref),
                error=error,
            )

            return

        finding = self._finding(decision, input_ref)

        memory.record(
            decision=decision,
            input_ref=self._compact_input_ref(input_ref),
            finding=finding,
        )

    def _finding(
        self,
        decision: dict[str, Any],
        input_ref: dict[str, Any],
    ) -> dict[str, Any] | None:
        raw_finding = decision.get("finding")
        if not isinstance(raw_finding, dict):
            return None

        confidence = decision.get("confidence", "low")
        category = raw_finding.get("category")
        tone = raw_finding.get("tone")
        explanation = raw_finding.get("explanation")
        source = self._source(input_ref)
        evidence = input_ref.get("value")

        if not (isinstance(category, str) and category):
            category = "unknown"

        if not (isinstance(tone, str) and tone):
            tone = "unknown"

        if not (isinstance(explanation, str) and explanation):
            explanation = "The dynamic evidence shows behavior relevant to malware analysis."

        return {
            "type": "dynamic_behavior",
            "confidence": confidence,
            "category": category,
            "tone": tone,
            "explanation": explanation,
            "source": source,
            "evidence": evidence,
        }


    def _compact_input_ref(self, input_ref: dict[str, Any]) -> dict[str, Any]:
        type = input_ref.get("type")
        tool = input_ref.get("tool")
        section = input_ref.get("section")
        index = input_ref.get("index")
        total_chunks = input_ref.get("total_chunks")
        total_items = input_ref.get("total_items")
        selected_count = input_ref.get("selected_count")

        return {
            "type": type,
            "tool": tool,
            "section": section,
            "index": index,
            "total_chunks": total_chunks,
            "total_items": total_items,
            "selected_count": selected_count,
            "value": None,
        }

    def _failed_decision(self) -> dict[str, Any]:
        return {
            "thought": "The dynamic evidence section could not be analyzed.",
            "confidence": "low",
            "action": "none",
            "parameters": {},
        }

    def _error_message(self, input_ref: dict[str, Any], exc: Exception) -> str:
        input = self._source(input_ref)

        return (
            f"Dynamic inference failed on {input}: {exc}"
        )

    def _source(self, input_ref: dict[str, Any]) -> str:
        tool = input_ref.get("tool", "unknown")
        section = input_ref.get("section", "unknown")
        index = input_ref.get("index")
        total_chunks = input_ref.get("total_chunks")

        if index and total_chunks:
            return f"{tool}.{section}.{index}/{total_chunks}"

        return f"{tool}.{section}"

    def _existing_explanations(self, memory: TraceMemory) -> list[str]:
        explanations = []

        for finding in memory.data.get("findings", []):
            if not isinstance(finding, dict):
                continue

            explanation = finding.get("explanation")
            if isinstance(explanation, str) and explanation.strip():
                explanations.append(explanation.strip())

        return explanations

    def _create_inference_model(self) -> DynamicInference:
        llm = self.model_registry.create_task_client(
            "dynamic",
            profile_override=self.context.profile,
        )

        return DynamicInference(llm)
