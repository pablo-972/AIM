from typing import Any

from core.ai.runtime.reversing.analysis import ReversingEvidenceAnalyzer
from core.ai.runtime.reversing.memory import ReversingAgentMemory
from core.ai.runtime.reversing.targets import ReversingTargetQueue
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

        for chunk_index, chunk in enumerate(chunks, start=1):
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
            decision_analysis = analysis
            follow_up, recovery_analysis, recovery_error = self._recover_follow_up(
                follow_up,
                target,
                observation,
                chunk,
                chunk_index,
                len(chunks),
            )
            if recovery_analysis is not None:
                decision_analysis = recovery_analysis
            error = self._merge_errors(error, recovery_error)

            follow_ups = []
            if follow_up is not None:
                follow_ups.append(follow_up)

            input_ref = self.postprocessor.input_ref(target, chunk_index)
            input_ref["total_chunks"] = len(chunks)

            decision = self.postprocessor.trace_decision(
                decision_analysis,
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

    def _recover_follow_up(
        self,
        follow_up: dict[str, Any] | None,
        target: dict[str, Any],
        observation: dict[str, Any],
        chunk: Any,
        chunk_index: int,
        total_chunks: int,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None]:
        if follow_up is None:
            return None, None, None

        rejection = self.targets.rejection_context(follow_up)
        if rejection is None:
            return follow_up, None, None

        self.targets.enqueue([follow_up], source="rejected_follow_up")
        recovery_context = self._recovery_context(follow_up, rejection)
        analysis, error = self.analyzer.recover_rejected_action(
            target,
            observation,
            chunk,
            chunk_index,
            total_chunks,
            recovery_context,
        )
        analysis = self.postprocessor.clean_analysis(analysis)

        recovered_follow_up = self.postprocessor.follow_up_target(
            analysis,
            target,
            observation,
        )
        if recovered_follow_up is None:
            return None, analysis, error

        recovered_rejection = self.targets.rejection_context(recovered_follow_up)
        if recovered_rejection is None:
            return recovered_follow_up, analysis, error

        self.targets.enqueue([recovered_follow_up], source="rejected_follow_up")
        return None, analysis, error

    def _recovery_context(
        self,
        follow_up: dict[str, Any],
        rejection: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "message": (
                "The requested target is not valid or could not be resolved "
                "unambiguously for the selected tool."
            ),
            "rejected_tool": follow_up.get("tool"),
            "rejected_parameters": follow_up.get("parameters"),
            "validator": rejection,
        }

    def _merge_errors(
        self,
        first: str | None,
        second: str | None,
    ) -> str | None:
        if first and second:
            return f"{first}; {second}"
        return first or second
