from typing import Any

from config import DYNAMIC_INFERENCE_RESULT_FILENAME
from core.utils.logger import Logger
from core.utils.preprocessing.dynamic.inference import prepare_dynamic_inference_inputs
from core.ai.inferences.dynamic import DynamicInference
from core.ai.runtime.dynamic_inference_memory import DynamicInferenceMemory
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
        memory = DynamicInferenceMemory(
            output_dir=self.context.output,
            filename=DYNAMIC_INFERENCE_RESULT_FILENAME,
            name="dynamic_inference",
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
        memory: DynamicInferenceMemory,
        input_ref: dict[str, Any],
    ) -> None:
        existing_summaries = self._existing_summaries(memory)

        try:
            decision = inference.analyze_section(input_ref, existing_summaries)
        except Exception as exc:
            error = self._error_message(input_ref, exc)
            Logger.error(error)

            memory.record(
                analysis=self._failed_analysis(),
                input_ref=self._compact_input_ref(input_ref),
                error=error,
            )

            return

        finding = self._finding(decision, input_ref)

        memory.record(
            analysis=self._analysis(decision),
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
        summary = raw_finding.get("summary")
        source = self._finding_source(input_ref)
        evidence = self._selected_evidence(raw_finding, input_ref)

        if not (isinstance(category, str) and category):
            category = "unknown"

        if not (isinstance(summary, str) and summary):
            summary = "The dynamic evidence shows behavior relevant to malware analysis."
        if not evidence:
            return None

        return {
            "type": "dynamic_behavior",
            "category": category,
            "confidence": confidence,
            "summary": summary,
            "evidence": evidence,
            "source": source,
        }


    def _compact_input_ref(self, input_ref: dict[str, Any]) -> dict[str, Any]:
        tool = input_ref.get("tool")
        section = input_ref.get("section")
        index = input_ref.get("index")
        total_chunks = input_ref.get("total_chunks")
        total_items = input_ref.get("total_items")
        selected_count = input_ref.get("selected_count")

        compact = {
            "source": tool,
            "section": section,
        }

        for key, value in (
            ("index", index),
            ("total_chunks", total_chunks),
            ("total_items", total_items),
            ("selected_count", selected_count),
        ):
            if value is not None:
                compact[key] = value

        return compact

    def _failed_analysis(self) -> dict[str, Any]:
        return {
            "thought": "The dynamic evidence section could not be analyzed.",
            "confidence": "low",
        }

    def _analysis(self, decision: dict[str, Any]) -> dict[str, Any]:
        thought = decision.get("thought")
        if not isinstance(thought, str):
            thought = ""

        return {
            "thought": thought,
            "confidence": decision.get("confidence", "low"),
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

    def _finding_source(self, input_ref: dict[str, Any]) -> dict[str, Any]:
        source = {
            "provider": input_ref.get("tool", "unknown"),
            "section": input_ref.get("section", "unknown"),
        }

        index = input_ref.get("index")
        if index is not None:
            source["chunk"] = index

        return source

    def _selected_evidence(
        self,
        raw_finding: dict[str, Any],
        input_ref: dict[str, Any],
    ) -> list[str]:
        raw_evidence = raw_finding.get("evidence")
        if not isinstance(raw_evidence, list):
            return []

        selected = []

        for item in raw_evidence:
            if not isinstance(item, str):
                continue

            value = item.strip()
            if not value:
                continue
            if value in selected:
                continue

            selected.append(value)

        return selected

    def _existing_summaries(self, memory: DynamicInferenceMemory) -> list[str]:
        summaries = []

        for finding in memory.data.get("findings", []):
            if not isinstance(finding, dict):
                continue

            summary = finding.get("summary")
            if isinstance(summary, str) and summary.strip():
                summaries.append(summary.strip())

        return summaries

    def _create_inference_model(self) -> DynamicInference:
        llm = self.model_registry.create_task_client(
            "dynamic",
            profile_override=self.context.profile,
        )

        return DynamicInference(llm)
