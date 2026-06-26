from typing import Any

from utils.postprocessing.reversing.contracts import (
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

        if target["tool"] not in CODE_FOLLOW_UP_TOOLS:
            return None

        if is_empty_code_observation(observation):
            return None

        if (
            target["tool"] == "function"
            and isinstance(observation.get("instructions_count"), int)
            and observation["instructions_count"] < 3
        ):
            return None

        code_targets = observation.get("code_targets")
        if (
            finding.get("type") == "critical_code_region"
            and not self._has_code_evidence(target, code_targets)
        ):
            return None

        self._normalize_location(finding, observation, code_targets)

        evidence = finding.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            return None
        return finding

    def _has_code_evidence(
        self,
        target: dict[str, Any],
        code_targets: Any,
    ) -> bool:
        return (
            target["tool"] in CODE_FOLLOW_UP_TOOLS
            or isinstance(code_targets, list) and bool(code_targets)
        )

    def _normalize_location(
        self,
        finding: dict[str, Any],
        observation: dict[str, Any],
        code_targets: Any,
    ) -> None:
        if finding.get("type") == "critical_code_region":
            if (
                not finding.get("function")
                and isinstance(code_targets, list)
                and code_targets
            ):
                finding["function"] = code_targets[0]

        resolved_function = observation.get("resolved_function")
        if isinstance(resolved_function, str) and resolved_function:
            finding["function"] = resolved_function

        start_address = observation.get("start_address")
        end_address = observation.get("end_address")
        if isinstance(start_address, str) and isinstance(end_address, str):
            finding["address_range"] = {
                "start": start_address,
                "end": end_address,
            }
        else:
            finding["address_range"] = None
