from typing import Any

from core.ai.runtime.reversing.analysis import ReversingEvidenceAnalyzer
from core.ai.runtime.reversing.fanout import (
    deterministic_chunk_follow_ups,
    deterministic_follow_ups,
)
from core.ai.runtime.reversing.memory import ReversingAgentMemory
from core.ai.runtime.reversing.targets import ReversingTargetQueue
from core.utils.logger import Logger
from core.utils.postprocessing.reversing import ReversingPostprocessor
from core.utils.preprocessing.reversing.assembly import chunk_reversing_evidence


class ReversingDecisionEvaluator:
    def __init__(
        self,
        analyzer: ReversingEvidenceAnalyzer,
        postprocessor: ReversingPostprocessor,
        memory: ReversingAgentMemory,
        targets: "ReversingTargetQueue",
    ) -> None:
        self.analyzer = analyzer
        self.postprocessor = postprocessor
        self.memory = memory
        self.targets = targets

    def evaluate(self, target: dict[str, Any], tool_output: dict[str, Any]) -> None:
        chunks = chunk_reversing_evidence(target["tool"], tool_output.get("data"))
        observation = self.postprocessor.observation_summary(target, tool_output)

        if target["tool"] != "disassembly":
            self._enqueue_deterministic_follow_ups(target, tool_output)

        for chunk_index, chunk in enumerate(chunks, start=1):
            deterministic_follow_ups_for_chunk = deterministic_chunk_follow_ups(
                target,
                tool_output,
                chunk,
            )
            analysis, error = self.analyzer.analyze_chunk(
                target,
                observation,
                chunk,
                chunk_index,
                len(chunks),
            )
            analysis = self.postprocessor.clean_analysis(analysis)

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
            follow_ups = list(deterministic_follow_ups_for_chunk)
            if follow_up is not None:
                follow_ups.append(follow_up)

            input_ref = self.postprocessor.input_ref(target, chunk_index)
            input_ref["total_chunks"] = len(chunks)

            decision = self.postprocessor.trace_decision(
                analysis,
                target,
                observation,
            )

            self.memory.record(
                decision=decision,
                tool_name=target["tool"],
                tool_parameters=target["parameters"],
                tool_output=tool_output,
                input_ref=input_ref,
                finding=finding,
                follow_ups=follow_ups,
                error=error,
            )

            if follow_ups:
                self.targets.enqueue(follow_ups, source="follow_up")

    def _enqueue_deterministic_follow_ups(
        self,
        target: dict[str, Any],
        tool_output: dict[str, Any],
    ) -> None:
        follow_ups = deterministic_follow_ups(target, tool_output)
        if not follow_ups:
            return

        added = self.targets.enqueue(follow_ups, source="follow_up")
        tool_name = target.get("tool")

        Logger.info(
            f"Queued {added}/{len(follow_ups)} deterministic reversing follow-ups "
            f"from {tool_name}"
        )
