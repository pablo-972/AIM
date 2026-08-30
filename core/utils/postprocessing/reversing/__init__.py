from typing import Any

from core.utils.postprocessing.reversing.findings import ReversingFindingValidator
from core.utils.postprocessing.reversing.model_output import ReversingModelOutputCleaner
from core.utils.postprocessing.reversing.observations import ReversingObservationBuilder
from core.utils.postprocessing.reversing.traces import ReversingTraceBuilder


class ReversingPostprocessor:
    def __init__(self, available_tools: dict[str, Any]) -> None:
        self._observations = ReversingObservationBuilder()
        self._findings = ReversingFindingValidator()
        self._model_output = ReversingModelOutputCleaner()
        self._traces = ReversingTraceBuilder()

    def clean_analysis(self, analysis: Any) -> dict[str, Any]:
        return self._model_output.clean(analysis)

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

    def follow_up_targets(
        self,
        analysis: dict[str, Any],
        target: dict[str, Any],
        observation: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return self._traces.build_follow_ups(analysis, target, observation)


__all__ = ["ReversingPostprocessor"]
