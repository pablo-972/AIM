from typing import Any

from core.utils.postprocessing.reversing.contracts import is_empty_code_observation

REVERSING_INVESTIGATION_TOOL_NAMES = {
    "disassembly",
    "callers",
    "callees",
    "inspect_section",
    "string_xrefs",
    "import_xrefs",
    "list_imports",
    "list_functions",
    "list_sections",
    "list_entrypoints",
}


class ReversingTraceBuilder:
    def __init__(self) -> None:
        pass

    def build_decision(
        self,
        analysis: dict[str, Any],
        target: dict[str, Any],
        observation: dict[str, Any],
    ) -> dict[str, Any]:
        summary = self._summary(analysis.get("summary"), observation)
        thinking = analysis.get("thinking")
        if not isinstance(thinking, list):
            thinking = []
        confidence = analysis.get("confidence", "low")

        return {
            "thinking": thinking,
            "summary": summary,
            "confidence": confidence,
        }

    def build_tool_calls(
        self,
        analysis: dict[str, Any],
        target: dict[str, Any],
        observation: dict[str, Any],
    ) -> list[dict[str, Any]]:
        tool_calls = analysis.get("tool_calls")
        if not isinstance(tool_calls, list):
            return []

        normalized_tool_calls = []
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue

            tool = tool_call.get("tool")
            parameters = tool_call.get("parameters")
            if (
                tool not in REVERSING_INVESTIGATION_TOOL_NAMES
                or not isinstance(parameters, dict)
            ):
                continue

            normalized_tool_call = {
                "tool": tool,
                "parameters": parameters,
                "priority": self._priority(tool_call, target),
            }
            normalized_tool_calls.append(normalized_tool_call)

        return normalized_tool_calls
    
    def _summary(self, summary: Any, observation: dict[str, Any]) -> str:
        normalized = summary.strip() if isinstance(summary, str) else ""
        normalized = self._strip_message_content_prefix(normalized)

        if not normalized:
            return "No decision summary was recorded."

        correction = self._correct_contradictory_summary(
            normalized,
            observation,
        )
        if correction:
            return correction

        if is_empty_code_observation(observation):
            return "No instructions were returned; no code conclusion was made."

        return normalized

    def _priority(
        self,
        tool_call: dict[str, Any],
        target: dict[str, Any],
    ) -> int:
        try:
            current_priority = int(target.get("priority", 50))
        except (TypeError, ValueError):
            current_priority = 50

        default = min(100, current_priority + 10)

        try:
            priority = int(tool_call.get("priority", default))
        except (TypeError, ValueError):
            priority = default

        return max(1, min(priority, 100))
    
    def _correct_contradictory_summary(
        self,
        summary: str,
        observation: dict[str, Any],
    ) -> str | None:
        lower = summary.lower()

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

    def _contradicts_matches(self, summary: str, observation: dict[str, Any]) -> bool:
        matches_count = observation.get("matches_count")

        return (
            isinstance(matches_count, int)
            and matches_count > 0
            and self._contains_any(summary, ("no match", "none were found"))
        )

    def _contradicts_xrefs(self, summary: str, observation: dict[str, Any]) -> bool:
        xrefs_count = observation.get("xrefs_count")

        return (
            isinstance(xrefs_count, int)
            and xrefs_count > 0
            and self._contains_any(summary, ("no cross-reference", "no xref"))
        )

    def _contains_any(self, text: str, phrases: tuple[str, ...]) -> bool:
        return any(phrase in text for phrase in phrases)

    def _strip_message_content_prefix(self, summary: str) -> str:
        prefix = "message.content:"
        if summary.lower().startswith(prefix):
            return summary[len(prefix):].lstrip()

        return summary

