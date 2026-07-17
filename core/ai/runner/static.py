from typing import Any
from config import STATIC_STRINGS_INFERENCE_RESULT_FILENAME
from core.utils.logger import Logger
from core.utils.preprocessing.static.strings import prepare_static_string_chunks
from core.ai.inferences.static import StaticInference
from core.ai.runtime.memory import TraceMemory
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
        memory = TraceMemory(
            output_dir=self.context.output,
            filename=STATIC_STRINGS_INFERENCE_RESULT_FILENAME,
            agent_name="static_strings_inference",
        )

        string_chunks = prepare_static_string_chunks(self.strings)

        try:
            for chunk_index, strings_chunk in enumerate(
                string_chunks,
                start=1,
            ):
                self._process_chunk(
                    inference,
                    memory,
                    chunk_index,
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
        memory: TraceMemory,
        chunk_index: int,
        strings_chunk: list[str],
    ) -> None:
        input_ref = self._input_ref(chunk_index)

        try:
            decision = inference.analyze_strings_chunk(strings_chunk)
        except Exception as exc:
            error = f"Static inference failed on chunk {chunk_index}: {exc}"
            Logger.error(error)

            memory.record(
                decision=self._failed_decision(),
                input_ref=input_ref,
                error=error,
            )
            return

        finding = self._finding(decision, strings_chunk)

        memory.record(
            decision=decision,
            input_ref=input_ref,
            finding=finding,
        )

    def _input_ref(self, chunk_index: int) -> dict[str, Any]:
        return {
            "type": "strings_chunk",
            "index": chunk_index,
            "value": None,
        }

    def _failed_decision(self) -> dict[str, Any]:
        return {
            "thought": "The chunk could not be analyzed.",
            "confidence": "low",
            "action": "none",
            "parameters": {},
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

        if not (isinstance(category, str) and category):
            category = "unknown"
        if not (isinstance(tone, str) and tone):
            tone = "unknown"

        return {
            "type": "threat_actor_message",
            "confidence": confidence,
            "text": strings_chunk,
            "category": category,
            "tone": tone,
        }

    def _create_inference_model(self) -> StaticInference:
        llm = self.model_registry.create_task_client(
            "static", 
            profile_override=self.context.profile,
        )
        return StaticInference(llm)
