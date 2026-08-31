from typing import Any

from core.ai.runtime.reversing.analysis import ReversingEvidenceAnalyzer
from core.ai.runtime.reversing.memory import ReversingAgentMemory
from core.ai.runtime.reversing.targets import ReversingTargetQueue
from core.ai.runtime.reversing.parameters import target_dedup_key
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

        self._evaluate_chunks(
            target=target,
            tool_output=tool_output,
            chunks=chunks,
            observation=observation,
            start_index=1,
        )

    def resume(self, target: dict[str, Any]) -> None:
        tool_output = target.get("_tool_output")
        chunks = target.get("_chunks")
        observation = target.get("_observation")
        start_index = target.get("_next_chunk_index")

        if (
            not isinstance(tool_output, dict)
            or not isinstance(chunks, list)
            or not isinstance(observation, dict)
            or not isinstance(start_index, int)
        ):
            return

        self._evaluate_chunks(
            target=target,
            tool_output=tool_output,
            chunks=chunks,
            observation=observation,
            start_index=start_index,
        )

    def review_global_state(self) -> int:
        analysis = self.analyzer.review_global_state(
            state=self.memory.global_review_state(),
            findings=self.memory.global_review_findings(),
            hypothesis=self.memory.hypothesis(),
        )
        analysis = self.postprocessor.clean_analysis(analysis)
        self.memory.update_hypothesis(analysis.get("hypothesis"))
        tool_calls = self.postprocessor.tool_call_targets(analysis, {}, {})
        added_tool_calls = self.targets.enqueue_targets(
            tool_calls,
            source="global_review",
        )
        decision = self.postprocessor.trace_decision(analysis, {}, {})
        self.memory.record(
            decision=decision,
            input_ref={
                "type": "global_review",
                "value": "queue_empty",
            },
            tool_calls=tool_calls,
        )
        return len(added_tool_calls)

    def _evaluate_chunks(
        self,
        target: dict[str, Any],
        tool_output: dict[str, Any],
        chunks: list[dict[str, Any]],
        observation: dict[str, Any],
        start_index: int,
    ) -> None:
        total_chunks = len(chunks)

        for index in range(start_index - 1, total_chunks):
            chunk_index = index + 1
            chunk = chunks[index]
            analysis, error = self.analyzer.analyze_chunk(
                target,
                observation,
                chunk,
                chunk_index,
                total_chunks,
                self._analysis_context(target, chunk_index, total_chunks),
            )
            analysis = self.postprocessor.clean_analysis(analysis)
            self.memory.update_hypothesis(analysis.get("hypothesis"))

            finding = self.postprocessor.finding(
                analysis.get("finding"),
                target,
                observation,
            )

            tool_calls = self.postprocessor.tool_call_targets(
                analysis,
                target,
                observation,
            )
            added_tool_calls = self.targets.enqueue_targets(
                tool_calls,
                source="native_tool_call",
            )

            input_ref = self.postprocessor.input_ref(target, chunk_index)
            input_ref["total_chunks"] = total_chunks

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
                tool_calls=tool_calls,
                error=error,
            )

            if added_tool_calls and chunk_index < total_chunks:
                self._enqueue_resume(
                    target,
                    tool_output,
                    chunks,
                    observation,
                    chunk_index + 1,
                )
                return

    def _enqueue_resume(
        self,
        target: dict[str, Any],
        tool_output: dict[str, Any],
        chunks: list[dict[str, Any]],
        observation: dict[str, Any],
        next_chunk_index: int,
    ) -> None:
        priority = self._resume_priority(target)
        resume_target = {
            **target,
            "_resume": True,
            "_queue_key": self._resume_key(target, next_chunk_index),
            "_tool_output": tool_output,
            "_chunks": chunks,
            "_observation": observation,
            "_next_chunk_index": next_chunk_index,
            "priority": priority,
        }
        self.targets.enqueue_resume(resume_target, source="pending_chunk")

    def _resume_key(self, target: dict[str, Any], next_chunk_index: int) -> str:
        return (
            "resume:"
            f"{target_dedup_key(target.get('tool'), target.get('parameters', {}))}:"
            f"{next_chunk_index}"
        )

    def _resume_priority(self, target: dict[str, Any]) -> int:
        try:
            priority = int(target.get("priority", 50))
        except (TypeError, ValueError):
            priority = 50

        return max(1, priority - 1)

    def _analysis_context(
        self,
        target: dict[str, Any],
        chunk_index: int,
        total_chunks: int,
    ) -> dict[str, Any]:
        return {}
