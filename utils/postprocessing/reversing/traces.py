from typing import Any

from utils.postprocessing.reversing.actions import ReversingActionPolicy
from utils.postprocessing.reversing.contracts import (
    NO_TOOL_ACTIONS,
    is_empty_code_observation,
)


class ReversingTraceBuilder:
    def __init__(self, action_policy: ReversingActionPolicy) -> None:
        self.action_policy = action_policy

    def build_decision(
        self,
        analysis: dict[str, Any],
        target: dict[str, Any],
        observation: dict[str, Any],
    ) -> dict[str, Any]:
        next_action, _ = self.action_policy.next_action(
            analysis,
            target,
            observation,
        )
        trace_action = (
            next_action if next_action in NO_TOOL_ACTIONS else target["tool"]
        )

        return {
            "thought": self._thought(analysis.get("thought"), observation),
            "confidence": analysis.get("confidence", "low"),
            "action": trace_action,
            "parameters": (
                {} if trace_action in NO_TOOL_ACTIONS else target["parameters"]
            ),
        }

    def build_follow_up(
        self,
        analysis: dict[str, Any],
        target: dict[str, Any],
        observation: dict[str, Any],
    ) -> dict[str, Any] | None:
        action, parameters = self.action_policy.next_action(
            analysis,
            target,
            observation,
        )
        if action in NO_TOOL_ACTIONS:
            return None

        return {
            "tool": action,
            "parameters": parameters,
            "priority": min(100, target["priority"] + 5),
            "reason": self._thought(
                analysis.get("thought"),
                observation,
            ) or f"Follow code evidence from {target['tool']}.",
        }

    def _thought(
        self,
        thought: Any,
        observation: dict[str, Any],
    ) -> str:
        normalized = str(thought or "").strip()
        lower = normalized.lower()
        matches_count = observation.get("matches_count")
        xrefs_count = observation.get("xrefs_count")

        if (
            isinstance(matches_count, int)
            and matches_count > 0
            and any(phrase in lower for phrase in ("no match", "none were found"))
        ):
            return (
                f"The tool returned {matches_count} matches; "
                "follow the reported code references."
            )

        if (
            isinstance(xrefs_count, int)
            and xrefs_count > 0
            and any(
                phrase in lower
                for phrase in ("no cross-reference", "no xref")
            )
        ):
            return (
                f"The tool returned {xrefs_count} code references; "
                "follow the reported functions or addresses."
            )

        if is_empty_code_observation(observation):
            return "No instructions were returned; no code conclusion was made."
        return normalized
