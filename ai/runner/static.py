from collections.abc import Iterator
from typing import Any
from config import STATIC_STRINGS_INFERENCE_RESULT_FILENAME
from utils.logger import Logger
from ai.inferences.static import StaticInference
from ai.runtime.memory import TraceMemory
from ai.runner.base import BaseAIRunner
from ai.model_registry import ModelRegistry
from orchestrator.context import AnalysisContext

STRING_CHUNK_SIZE = 80


class StaticInferenceRunner(BaseAIRunner):
    def __init__(
        self,
        context: AnalysisContext,
        model_registry: ModelRegistry,
        strings: list[str],
    ) -> None:
        super().__init__(context)

        self.model_registry: ModelRegistry = model_registry
        self.strings: list[str] = strings
        
    def run(self) -> None:
        Logger.info("Running static strings AI inference")

        llm = self.model_registry.create_task_client(
            "static", 
            profile_override=self.context.profile
        )
        inference = StaticInference(llm)
        memory = TraceMemory(
            output_dir=self.context.output,
            filename=STATIC_STRINGS_INFERENCE_RESULT_FILENAME,
            agent_name="static_strings_inference",
        )

        try:
            for chunk_index, strings_chunk in enumerate(self._iter_string_chunks(), start=1):
                input_ref = {
                    "type": "strings_chunk",
                    "index": chunk_index,
                    "value": None,
                }

                try:
                    decision = inference.analyze_strings_chunk(strings_chunk)
                except Exception as exc:
                    error = f"Static inference failed on chunk {chunk_index}: {exc}"
                    Logger.error(error)
                    memory.record(
                        decision={
                            "thought": "The chunk could not be analyzed.",
                            "confidence": "low",
                            "action": "none",
                            "parameters": {},
                        },
                        input_ref=input_ref,
                        error=error,
                    )
                    continue

                finding = self._finding(decision, strings_chunk)
                memory.record(
                    decision=decision,
                    input_ref=input_ref,
                    finding=finding,
                )
        except Exception as exc:
            memory.fail(str(exc))
            raise
        else:
            memory.close()

        Logger.success("Static strings AI inference finished")
    
    def _iter_string_chunks(self, chunk_size: int = STRING_CHUNK_SIZE) -> Iterator[list[str]]:
        for index in range(0, len(self.strings), chunk_size):
            yield self.strings[index:index + chunk_size]

    def _finding(
        self,
        decision: dict[str, Any],
        strings_chunk: list[str],
    ) -> dict[str, Any] | None:
        raw_finding = decision.get("finding")
        if not isinstance(raw_finding, dict):
            return None

        category = raw_finding.get("category")
        tone = raw_finding.get("tone")
        return {
            "type": "threat_actor_message",
            "confidence": decision.get("confidence", "low"),
            "text": strings_chunk,
            "category": category if isinstance(category, str) and category else "unknown",
            "tone": tone if isinstance(tone, str) and tone else "unknown",
        }
