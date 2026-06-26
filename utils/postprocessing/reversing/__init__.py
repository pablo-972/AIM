from typing import Any

from utils.postprocessing.reversing.actions import ReversingActionPolicy
from utils.postprocessing.reversing.findings import ReversingFindingValidator
from utils.postprocessing.reversing.observations import ReversingObservationBuilder
from utils.postprocessing.reversing.traces import ReversingTraceBuilder


class ReversingPostprocessor:
    def __init__(self, available_tools: dict[str, Any]) -> None:
        self._observations = ReversingObservationBuilder()
        self._actions = ReversingActionPolicy(available_tools)
        self._findings = ReversingFindingValidator()
        self._traces = ReversingTraceBuilder(self._actions)

    def input_ref(
        self,
        target: dict[str, Any],
        chunk_index: int | None = None,
    ) -> dict[str, Any]:
        return self._observations.input_ref(target, chunk_index)

    def observation_summary(
        self,
        target: dict[str, Any],
        tool_output: dict[str, Any],
    ) -> dict[str, Any]:
        return self._observations.build_summary(target, tool_output)

    def finding(
        self,
        finding: Any,
        target: dict[str, Any],
        observation: dict[str, Any],
    ) -> dict[str, Any] | None:
        return self._findings.validate(finding, target, observation)

    def trace_decision(
        self,
        analysis: dict[str, Any],
        target: dict[str, Any],
        observation: dict[str, Any],
    ) -> dict[str, Any]:
        return self._traces.build_decision(analysis, target, observation)

    def follow_up_target(
        self,
        analysis: dict[str, Any],
        target: dict[str, Any],
        observation: dict[str, Any],
    ) -> dict[str, Any] | None:
        return self._traces.build_follow_up(analysis, target, observation)

    def next_action(
        self,
        analysis: dict[str, Any],
        target: dict[str, Any],
        observation: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        return self._actions.next_action(analysis, target, observation)


__all__ = ["ReversingPostprocessor"]
