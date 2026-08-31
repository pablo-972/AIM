from typing import Any

from core.utils.postprocessing.reversing.contracts import (
    CODE_FOLLOW_UP_TOOLS,
    is_empty_code_observation,
)
from core.utils.address import parse_address


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

        if self._is_too_small_disassembly(tool, observation):
            return None

        normalized = dict(finding)
        code_targets = observation.get("code_targets")
        self._normalize_evidence(normalized)

        if (
            normalized.get("type") == "critical_code_region"
            and not self._has_code_evidence(code_targets)
        ):
            return None

        self._normalize_location(normalized, observation, code_targets)

        evidence = normalized.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            return None

        return normalized


    def _is_too_small_disassembly(
        self,
        tool: Any,
        observation: dict[str, Any],
    ) -> bool:
        instructions_count = observation.get("instructions_count")

        return (
            tool == "disassembly"
            and isinstance(instructions_count, int)
            and instructions_count < 3
        )

    def _has_code_evidence(self, code_targets: Any) -> bool:
        return isinstance(code_targets, list) and bool(code_targets)

    def _normalize_evidence(self, finding: dict[str, Any]) -> None:
        evidence = finding.get("evidence")
        if isinstance(evidence, str):
            evidence = [evidence]
        if not isinstance(evidence, list):
            finding["evidence"] = []
            return

        finding["evidence"] = [
            item.strip()
            for item in evidence
            if isinstance(item, str) and item.strip()
        ]

    def _normalize_location(
        self,
        finding: dict[str, Any],
        observation: dict[str, Any],
        code_targets: Any,
    ) -> None:
        if finding.get("type") == "critical_code_region":
            self._set_default_function(finding, code_targets)

        self._set_function_name(finding, observation)
        self._remove_address_like_function(finding)
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

    def _set_function_name(
        self,
        finding: dict[str, Any],
        observation: dict[str, Any],
    ) -> None:
        function = observation.get("function")

        if isinstance(function, str) and function:
            finding["function"] = function

    def _remove_address_like_function(self, finding: dict[str, Any]) -> None:
        function = finding.get("function")
        if not isinstance(function, str):
            return

        if (
            parse_address(function) is not None
            or _looks_like_generated_address_label(function)
        ):
            finding.pop("function", None)

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
        elif "address_range" not in finding:
            finding["address_range"] = None


def _looks_like_generated_address_label(name: str) -> bool:
    lowered = name.strip().lower()
    for prefix in ("fcn.", "sub."):
        if lowered.startswith(prefix) and _is_hex_text(lowered[len(prefix):]):
            return True

    return False


def _is_hex_text(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized.startswith("0x"):
        normalized = normalized[2:]

    return bool(normalized) and all(
        character in "0123456789abcdef"
        for character in normalized
    )
