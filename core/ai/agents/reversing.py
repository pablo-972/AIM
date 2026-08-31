import json
from typing import Any

from core.ai.providers.base import BaseLLMProvider
from core.ai.agents.reversing_tools_definition import (
    build_reversing_tool_definitions,
    tool_calls_to_targets,
)
from core.tools.reversing.agent import REVERSING_AGENT_TOOL_NAMES


SYSTEM_PROMPT = """
You are a malware reverse-engineering analyst.

Analyze the current reversing evidence conservatively using symbols, assembly,
control flow and data flow.

Base follow-up investigation primarily on the current tool output and accumulated
reversing findings. Initialization context is guidance, not a reason to repeatedly
revisit the same artifacts.

Record findings when direct reversing evidence supports meaningful behavior.
Prefer exact address: instruction evidence.
Prefer these categories when they fit: file_encryption, crypto,
defense_evasion, network, persistence, privilege_escalation, api_resolution,
anti_analysis, unknown.
A finding must represent meaningful behavior. Generic UI code, register setup,
stack manipulation or an unresolved call is normally context, not a finding.
Do not create a finding merely because a chunk can be described. Prologue,
epilogue, stack/register manipulation, arithmetic, generic control flow, and
unresolved calls are not findings by themselves.

Use native tools when additional evidence would materially improve the analysis.
Do not continue merely because tools remain available.

Prefer following a strong concrete lead before continuing unrelated broad output.
Pending work is preserved and may be resumed later.

Discovery is candidate collection, not winner selection. Preserve multiple clearly
promising independent targets when useful.
Treat discovery outputs (list_functions, list_imports, list_sections,
list_entrypoints) as candidate sources, not as evidence that must produce a
finding. Evaluate each discovery chunk independently; do not wait for all
chunks before acting. If the current discovery chunk contains concrete promising
targets, emit the corresponding native tool calls immediately. For
list_functions, inspect promising functions with disassembly(function=...). For
imports, use import_xrefs(...) when useful. Do not return no tool calls merely
because a discovery output does not support a finding.
If your reasoning says that a concrete function, address, import, section or
entrypoint should be inspected next, you MUST issue the corresponding native
tool call in the same response. Do not describe a next investigation without
performing it.

Do not call tools merely to keep the investigation moving.
Avoid work that has already been executed or is already pending.

When semantics remain unclear, prefer further evidence or a structural
interpretation over unsupported conclusions.

When writing message content, start with a short summary. Do not include labels
such as message.content.
Detailed reasoning belongs in Ollama thinking. Message content must be only a
short decision summary.

Do not use tool calls for findings. Native tool calls are only for investigation
targets.
Findings and tool calls are independent: recording a finding does not terminate
the branch. If there is a valid finding and promising targets remain, produce
both the finding in message content and native investigation tool calls in the
same response.
"""

class ReversingAgent:
    def __init__(self, llm: BaseLLMProvider) -> None:
        self.llm = llm

    def create_initial_targets(
        self,
        enrichment: str,
        available_tools: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = f"""
        Select the initial reversing targets and emit them as native tool calls.
        You may emit multiple independent tool calls. Message content must be
        only a short decision summary.

        Enrichment context:
        {enrichment or "No enrichment is available."}

        Prioritize targets that can lead to critical code regions:
        - suspicious imports with import_xrefs
        - behaviorally meaningful strings with string_xrefs
        - concrete internal code addresses with disassembly
        - focused discovery tools when enrichment does not provide enough
          concrete targets

        If no enrichment is available, start with compact discovery tool calls
        instead of guessing targets. Prefer list_imports, list_sections, and
        list_entrypoints first; use list_functions when internal code candidates
        are needed. Discovery tools do not require parameters.

        Skip generic file extensions, wildcard patterns, short fragments, and
        boilerplate runtime strings unless they are unusual, grouped with many
        target extensions, or connected to stronger malware behavior evidence.
        Do not prioritize wallet, payment, contact, Session, or onion strings unless
        they are needed to locate ransom-note generation code. Do not invent addresses.
        Keep the initial queue focused.
        """

        reversing_tool_definitions = build_reversing_tool_definitions(
            available_tools,
        )

        response = self.llm.chat_tools(
            SYSTEM_PROMPT,
            prompt,
            reversing_tool_definitions,
        )

        summary = self._response_summary(response.content, response.tool_calls)
        targets = tool_calls_to_targets(
            response.tool_calls,
            priority=70,
        )

        return {
            "summary": summary,
            "thinking": list(response.thinking),
            "targets": targets,
        }

    def analyze_evidence(
        self,
        target: dict[str, Any],
        observation: dict[str, Any],
        chunk: Any,
        chunk_index: int,
        total_chunks: int,
        available_tools: dict[str, Any],
        analysis_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        compact_target = self._compact_target(target)
        chunk_text = self._format_chunk_for_prompt(chunk)
        context_text = self._format_analysis_context(analysis_context)

        prompt = f"""
        Analyze this evidence chunk.

        Current input target:
        {json.dumps(compact_target, ensure_ascii=False, default=str)}

        Tool output summary:
        {json.dumps(observation, ensure_ascii=False, default=str)}

        Bounded raw tool chunk {chunk_index} of {total_chunks}:
        {chunk_text}

        Local reversing context:
        {context_text}

        Use native tool calls only for additional investigation tools. Do not use
        tool calls for findings. If direct evidence supports one meaningful
        finding, append one final line beginning with finding: followed by a JSON
        object with summary, category, confidence, evidence as an array of
        strings, function and address_range. If a finding and additional
        investigation are both useful, emit both the finding line in message
        content and native investigation tool calls in the same response. If no
        further local action is useful, emit no tool calls.
        """

        reversing_tool_definitions = build_reversing_tool_definitions(
            available_tools,
        )

        response = self.llm.chat_tools(
            SYSTEM_PROMPT,
            prompt,
            reversing_tool_definitions,
        )

        finding = self._response_finding(response.content)
        tool_calls = tool_calls_to_targets(
            response.tool_calls,
            priority=self._default_tool_call_priority(target),
        )
        summary = self._response_summary(
            response.content,
            response.tool_calls,
            finding,
        )
        confidence = "medium"
        if isinstance(finding, dict) and finding.get("confidence") in {
            "low",
            "medium",
            "high",
        }:
            confidence = finding["confidence"]

        return {
            "summary": summary,
            "thinking": list(response.thinking),
            "confidence": confidence,
            "tool_calls": tool_calls,
            "finding": finding,
        }

    def review_global_state(
        self,
        state: dict[str, Any],
        hypothesis: dict[str, Any],
        available_tools: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = f"""
        Review the global reversing investigation after the local queue became
        empty.

        Factual global state:
        {json.dumps(state, ensure_ascii=False, default=str)}

        Current model hypothesis:
        {json.dumps(hypothesis, ensure_ascii=False, default=str)}

        Decide whether there is still a reasonable path to materially improve
        the analysis. If yes, emit native investigation tool calls. Consider
        list_functions, list_imports, list_sections, or list_entrypoints when
        structural areas remain undiscovered and they are likely to add useful
        evidence. Do not force discovery tools mechanically. If no further local
        action is useful, emit no tool calls. Message content must start with a
        short decision summary.

        Update the global hypothesis from the investigation evidence during this
        review. Append one final line beginning with hypothesis: followed by a
        JSON object with malware, type, and confidence. malware must be true,
        false, or null. type may be null.
        """

        response = self.llm.chat_tools(
            SYSTEM_PROMPT,
            prompt,
            build_reversing_tool_definitions(available_tools),
        )
        tool_calls = tool_calls_to_targets(response.tool_calls, priority=50)

        return {
            "summary": self._response_summary(response.content, response.tool_calls),
            "thinking": list(response.thinking),
            "confidence": "medium",
            "tool_calls": tool_calls,
            "hypothesis": self._response_hypothesis(response.content),
        }

    def _compact_target(self, target: dict[str, Any]) -> dict[str, Any]:
        return {
            "tool": target["tool"],
            "parameters": target["parameters"],
        }

    def _format_chunk_for_prompt(
        self,
        chunk: Any,
    ) -> str:
        if isinstance(chunk, dict):
            section = chunk.get("section")
            data = chunk.get("data")

            if isinstance(section, str):
                if section.startswith("disassembly.instructions."):
                    if isinstance(data, str):
                        return f"{section}\n{data}"

        return json.dumps(chunk, ensure_ascii=False, default=str)

    def _response_summary(
        self,
        content: str,
        tool_calls: Any,
        finding: dict[str, Any] | None = None,
    ) -> str:
        summary = self._clean_message_content(content)
        if summary:
            return summary

        if isinstance(finding, dict):
            finding_summary = finding.get("summary")
            if isinstance(finding_summary, str) and finding_summary.strip():
                return finding_summary.strip()

        targets = tool_calls_to_targets(tool_calls, priority=50)
        if targets:
            tool_names = [
                target["tool"]
                for target in targets[:3]
                if isinstance(target.get("tool"), str)
            ]
            if tool_names:
                return "Model requested further evidence with " + ", ".join(tool_names)

        return "Model did not request additional reversing work for this chunk."

    def _clean_message_content(self, content: str) -> str:
        if not isinstance(content, str):
            return ""

        cleaned = content.strip()
        prefix = "message.content:"
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):].lstrip()

        if self._content_is_only_finding(cleaned):
            return ""

        for marker in self._text_tool_markers():
            position = cleaned.find(marker)
            if position == 0:
                return ""
            if position > 0:
                cleaned = cleaned[:position].rstrip()

        for marker in self._finding_markers():
            position = cleaned.lower().find(marker)
            if position == 0:
                return ""
            if position > 0:
                cleaned = cleaned[:position].rstrip()

        for marker in self._hypothesis_markers():
            position = cleaned.lower().find(marker)
            if position == 0:
                return ""
            if position > 0:
                cleaned = cleaned[:position].rstrip()

        return cleaned

    def _content_is_only_finding(self, content: str) -> bool:
        stripped = content.lstrip()
        if not stripped.startswith(("{", "[")):
            return False

        return self._finding_from_decoded(
            self._decode_first_json_value(stripped)
        ) is not None

    def _text_tool_markers(self) -> tuple[str, ...]:
        tool_names = [
            "record_finding",
            *REVERSING_AGENT_TOOL_NAMES,
        ]
        markers = []
        for tool_name in tool_names:
            markers.extend(
                (
                    f"\n{tool_name}{{",
                    f"\n\n{tool_name}{{",
                    f"\n{tool_name}(",
                    f"\n\n{tool_name}(",
                )
            )

        return tuple(markers)

    def _response_finding(self, content: str) -> dict[str, Any] | None:
        if not isinstance(content, str):
            return None

        for marker in self._finding_markers():
            position = content.lower().find(marker)
            if position < 0:
                continue

            decoded = self._decode_first_json_value(content[position + len(marker):])
            finding = self._finding_from_decoded(decoded)
            if finding is not None:
                return finding

        decoded = self._decode_first_json_value(content)
        return self._finding_from_decoded(decoded)

    def _finding_markers(self) -> tuple[str, ...]:
        return (
            "\nfinding:",
            "\nfinding =",
            "finding:",
            "finding =",
        )

    def _response_hypothesis(self, content: str) -> dict[str, Any] | None:
        if not isinstance(content, str):
            return None

        lowered = content.lower()
        for marker in self._hypothesis_markers():
            position = lowered.find(marker)
            if position < 0:
                continue

            decoded = self._decode_first_json_value(content[position + len(marker):])
            return decoded if isinstance(decoded, dict) else None

        return None

    def _hypothesis_markers(self) -> tuple[str, ...]:
        return (
            "\nhypothesis:",
            "\nhypothesis =",
            "hypothesis:",
            "hypothesis =",
        )

    def _decode_first_json_value(self, text: str) -> Any:
        start = self._json_start(text)
        if start < 0:
            return None

        try:
            decoded, _ = json.JSONDecoder().raw_decode(text[start:])
        except json.JSONDecodeError:
            return None

        return decoded

    def _json_start(self, text: str) -> int:
        starts = [
            position
            for position in (text.find("{"), text.find("["))
            if position >= 0
        ]
        if not starts:
            return -1

        return min(starts)

    def _finding_from_decoded(self, decoded: Any) -> dict[str, Any] | None:
        if isinstance(decoded, list):
            for item in decoded:
                finding = self._finding_from_decoded(item)
                if finding is not None:
                    return finding

            return None

        if not isinstance(decoded, dict):
            return None

        nested_finding = decoded.get("finding")
        if isinstance(nested_finding, dict):
            return nested_finding

        if self._looks_like_finding(decoded):
            return decoded

        return None

    def _looks_like_finding(self, value: dict[str, Any]) -> bool:
        evidence = value.get("evidence")
        return (
            isinstance(value.get("summary"), str)
            and isinstance(value.get("confidence"), str)
            and isinstance(evidence, (list, str))
        )

    def _default_tool_call_priority(self, target: dict[str, Any]) -> int:
        try:
            priority = int(target.get("priority", 50))
        except (TypeError, ValueError):
            priority = 50

        return min(100, priority + 10)

    def _format_analysis_context(
        self,
        analysis_context: dict[str, Any] | None,
    ) -> str:
        if not isinstance(analysis_context, dict):
            analysis_context = {}

        return json.dumps(analysis_context, ensure_ascii=False, default=str)
