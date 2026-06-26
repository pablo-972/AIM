from typing import Any

from utils.logger import Logger
from utils.postprocessing.reversing import ReversingPostprocessor
from utils.preprocessing.reversing import chunk_reversing_evidence
from ai.agents.reversing import ReversingAgent
from ai.runtime.memory import TraceMemory
from ai.runtime.reversing.targets import ReversingTargetQueue


class ReversingEvidenceEvaluator:
    def __init__(
        self,
        agent: ReversingAgent,
        enrichment: str,
        available_tools: dict[str, Any],
        postprocessor: ReversingPostprocessor,
        memory: "TraceMemory",
        targets: "ReversingTargetQueue",
    ) -> None:
        self.agent = agent
        self.enrichment = enrichment
        self.available_tools = available_tools
        self.postprocessor = postprocessor
        self.memory = memory
        self.targets = targets

    def evaluate(
        self,
        target: dict[str, Any],
        tool_output: dict[str, Any],
    ) -> None:
        chunks = chunk_reversing_evidence(
            target["tool"],
            tool_output.get("data"),
        )
        observation = self.postprocessor.observation_summary(
            target,
            tool_output,
        )

        for chunk_index, chunk in enumerate(chunks, start=1):
            analysis, error = self._analyze_chunk(
                target,
                observation,
                chunk,
                chunk_index,
                len(chunks),
            )
            finding = self.postprocessor.finding(
                analysis.get("finding"),
                target,
                observation,
            )
            follow_up = self.postprocessor.follow_up_target(
                analysis,
                target,
                observation,
            )
            self.memory.record(
                decision=self.postprocessor.trace_decision(
                    analysis,
                    target,
                    observation,
                ),
                tool_name=target["tool"],
                tool_output=tool_output,
                input_ref=self.postprocessor.input_ref(target, chunk_index),
                finding=finding,
                error=error,
            )
            if follow_up is not None:
                self.targets.enqueue([follow_up], source="follow_up")

    def _analyze_chunk(
        self,
        target: dict[str, Any],
        observation: dict[str, Any],
        chunk: Any,
        chunk_index: int,
        total_chunks: int,
    ) -> tuple[dict[str, Any], str | None]:
        try:
            return self._request_analysis(
                self.enrichment,
                target,
                observation,
                chunk,
                chunk_index,
                total_chunks,
            ), None
        except Exception as first_exc:
            return self._retry_without_enrichment(
                first_exc,
                target,
                observation,
                chunk,
                chunk_index,
                total_chunks,
            )

    def _retry_without_enrichment(
        self,
        first_exc: Exception,
        target: dict[str, Any],
        observation: dict[str, Any],
        chunk: Any,
        chunk_index: int,
        total_chunks: int,
    ) -> tuple[dict[str, Any], str | None]:
        try:
            Logger.warning(
                f"Retrying {target['tool']} chunk {chunk_index} "
                "without enrichment context"
            )
            analysis = self._request_analysis(
                "",
                target,
                observation,
                chunk,
                chunk_index,
                total_chunks,
            )
            return analysis, None
        except Exception as retry_exc:
            error = (
                f"Initial LLM error: {first_exc}; "
                f"compact retry error: {retry_exc}"
            )
            Logger.error(
                f"Reversing agent failed for {target['tool']} "
                f"chunk {chunk_index}: {error}"
            )
            return {
                "thought": "LLM decision failed.",
                "confidence": "low",
                "action": "none",
                "parameters": {},
                "finding": None,
            }, error

    def _request_analysis(
        self,
        enrichment: str,
        target: dict[str, Any],
        observation: dict[str, Any],
        chunk: Any,
        chunk_index: int,
        total_chunks: int,
    ) -> dict[str, Any]:
        return self.agent.analyze_evidence(
            enrichment=enrichment,
            target=target,
            observation=observation,
            chunk=chunk,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            available_tools=self.available_tools,
        )
