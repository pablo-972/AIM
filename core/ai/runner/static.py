from typing import Any
from config import STATIC_INFERENCE_RESULT_FILENAME
from core.utils.logger import Logger
from core.utils.preprocessing.static.strings import prepare_static_string_chunks
from core.ai.inferences.static import StaticInference
from core.ai.runtime.inference.static_memory import StaticInferenceMemory
from core.ai.runner.base import BaseAIRunner
from core.ai.model_registry import ModelRegistry
from core.orchestrator.context import AnalysisContext


class StaticInferenceRunner(BaseAIRunner):
    def __init__(
        self,
        context: AnalysisContext,
        model_registry: ModelRegistry,
        strings: list[str],
    ) -> None:
        super().__init__(context)

        self.model_registry = model_registry
        self.strings: list[str] = strings
        
    def run(self) -> None:
        inference = self._create_inference_model()
        memory = StaticInferenceMemory(
            output_dir=self.context.output,
            filename=STATIC_INFERENCE_RESULT_FILENAME,
            agent_name="static_strings_inference",
        )

        string_chunks = prepare_static_string_chunks(self.strings)
        total_chunks = len(string_chunks)

        try:
            for chunk_index, strings_chunk in enumerate(string_chunks, start=1):
                self._process_chunk(
                    inference,
                    memory,
                    chunk_index,
                    total_chunks,
                    strings_chunk,
                )
        except Exception as exc:
            memory.fail(str(exc))
            raise
        else:
            memory.close()


    def _process_chunk(
        self,
        inference: StaticInference,
        memory: StaticInferenceMemory,
        chunk_index: int,
        total_chunks: int,
        strings_chunk: list[str],
    ) -> None:
        input_ref = self._input_ref(chunk_index, total_chunks)

        try:
            decision = inference.analyze_strings_chunk(strings_chunk)
        except Exception as exc:
            error = f"Static inference failed on chunk {chunk_index}: {exc}"
            Logger.error(error)

            memory.record(
                analysis=self._failed_analysis(),
                input_ref=input_ref,
                error=error,
            )
            return

        finding = self._finding(decision, strings_chunk)

        memory.record(
            analysis=self._analysis(decision),
            input_ref=input_ref,
            finding=finding,
        )

    def _input_ref(self, chunk_index: int, total_chunks: int) -> dict[str, Any]:
        return {
            "type": "strings_chunk",
            "index": chunk_index,
            "total_chunks": total_chunks,
        }

    def _failed_analysis(self) -> dict[str, Any]:
        return {
            "thought": "The chunk could not be analyzed.",
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
    
    def _finding(
        self,
        decision: dict[str, Any],
        strings_chunk: list[str],
    ) -> dict[str, Any] | None:
        confidence = decision.get("confidence", "low")
        raw_finding = decision.get("finding")
        if not isinstance(raw_finding, dict):
            return None

        category = raw_finding.get("category")
        tone = raw_finding.get("tone")
        summary = raw_finding.get("summary")
        evidence = self._selected_evidence(raw_finding, strings_chunk)

        if not (isinstance(category, str) and category):
            category = "unknown"
        if not (isinstance(tone, str) and tone):
            tone = "unknown"
        if not (isinstance(summary, str) and summary):
            summary = "Victim-facing threat actor message detected."
        if not evidence:
            return None

        return {
            "type": "threat_actor_message",
            "category": category,
            "confidence": confidence,
            "tone": tone,
            "summary": summary,
            "evidence": evidence,
        }

    def _selected_evidence(
        self,
        raw_finding: dict[str, Any],
        strings_chunk: list[str],
    ) -> list[str]:
        raw_evidence = raw_finding.get("evidence")
        if not isinstance(raw_evidence, list):
            return []

        chunk_strings = set(strings_chunk)
        selected = []

        for item in raw_evidence:
            if not isinstance(item, str):
                continue

            value = item.strip()
            if not value:
                continue
            if value not in chunk_strings:
                continue
            if value in selected:
                continue

            selected.append(value)

        return selected

    def _create_inference_model(self) -> StaticInference:
        llm = self.model_registry.create_task_client(
            "static", 
            profile_override=self.context.profile,
        )
        return StaticInference(llm)
