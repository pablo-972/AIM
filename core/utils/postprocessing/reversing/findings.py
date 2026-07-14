from typing import Any

from core.utils.postprocessing.reversing.contracts import (
    CODE_FOLLOW_UP_TOOLS,
    is_empty_code_observation,
)


class ReversingFindingValidator:
    def validate(
        self,
        finding: Any,
        target: dict[str, Any],
        observation: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not isinstance(finding, dict):
            return None

        tool = target.get("tool")
        if tool not in CODE_FOLLOW_UP_TOOLS:
            return None

        if is_empty_code_observation(observation):
            return None

        if self._is_too_small_function(tool, observation):
            return None

        normalized = dict(finding)
        code_targets = observation.get("code_targets")

        if (
            normalized.get("type") == "critical_code_region"
            and not self._has_code_evidence(code_targets)
        ):
            return None

        self._normalize_location(finding, observation, code_targets)

        evidence = finding.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            return None
        
        return normalized
    

    def _is_too_small_function(
        self,
        tool: Any,
        observation: dict[str, Any],
    ) -> bool:
        instructions_count = observation.get("instructions_count")

        return (
            tool == "function"
            and isinstance(instructions_count, int)
            and instructions_count < 3
        )

    def _has_code_evidence(self, code_targets: Any) -> bool:
        return isinstance(code_targets, list) and bool(code_targets)

    def _normalize_location(
        self,
        finding: dict[str, Any],
        observation: dict[str, Any],
        code_targets: Any,
    ) -> None:
        if finding.get("type") == "critical_code_region":
            self._set_default_function(finding, code_targets)

        self._set_resolved_function(finding, observation)
        self._set_address_range(finding, observation)

    def _set_default_function(
        self,
        finding: dict[str, Any],
        code_targets: Any,
    ) -> None:
        if finding.get("function"):
            return

        if isinstance(code_targets, list) and code_targets:
            finding["function"] = code_targets[0]

    def _set_resolved_function(
        self,
        finding: dict[str, Any],
        observation: dict[str, Any],
    ) -> None:
        resolved_function = observation.get("resolved_function")

        if isinstance(resolved_function, str) and resolved_function:
            finding["function"] = resolved_function

    def _set_address_range(
        self,
        finding: dict[str, Any],
        observation: dict[str, Any],
    ) -> None:
        start_address = observation.get("start_address")
        end_address = observation.get("end_address")

        if isinstance(start_address, str) and isinstance(end_address, str):
            finding["address_range"] = {
                "start": start_address,
                "end": end_address,
            }
        else:
            finding["address_range"] = None