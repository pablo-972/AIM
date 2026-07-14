from typing import Any

from core.utils.postprocessing.reversing.actions import ReversingActionPolicy
from core.utils.postprocessing.reversing.contracts import (
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
            next_action
            if next_action in NO_TOOL_ACTIONS
            else target.get("tool")
        )

        parameters = {}
        if trace_action not in NO_TOOL_ACTIONS:
            parameters = target.get("parameters")

        return {
            "thought": self._thought(analysis.get("thought"), observation),
            "confidence": analysis.get("confidence", "low"),
            "action": trace_action,
            "parameters": parameters,
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
        
        reason = self._thought(analysis.get("thought"), observation)
        if not reason:
            reason = f"Follow code evidence from {target.get("tool")}."

        return {
            "tool": action,
            "parameters": parameters,
            "priority": min(100, target["priority"] + 5),
            "reason": reason
        }
    
    def _thought(self, thought: Any, observation: dict[str, Any]) -> str:
        normalized = str(thought or "").strip()

        correction = self._correct_contradictory_thought(normalized, observation)
        if correction:
            return correction

        if is_empty_code_observation(observation):
            return "No instructions were returned; no code conclusion was made."

        return normalized
    
    def _correct_contradictory_thought(
        self,
        thought: str,
        observation: dict[str, Any],
    ) -> str | None:
        lower = thought.lower()

        if self._contradicts_matches(lower, observation):
            return (
                f"The tool returned {observation['matches_count']} matches; "
                "follow the reported code references."
            )

        if self._contradicts_xrefs(lower, observation):
            return (
                f"The tool returned {observation['xrefs_count']} code references; "
                "follow the reported functions or addresses."
            )

        return None

    def _contradicts_matches(self, thought: str, observation: dict[str, Any]) -> bool:
        matches_count = observation.get("matches_count")

        return (
            isinstance(matches_count, int)
            and matches_count > 0
            and self._contains_any(thought, ("no match", "none were found"))
        )

    def _contradicts_xrefs(self, thought: str, observation: dict[str, Any]) -> bool:
        xrefs_count = observation.get("xrefs_count")

        return (
            isinstance(xrefs_count, int)
            and xrefs_count > 0
            and self._contains_any(thought, ("no cross-reference", "no xref"))
        )

    def _contains_any(self, text: str, phrases: tuple[str, ...]) -> bool:
        return any(phrase in text for phrase in phrases)

