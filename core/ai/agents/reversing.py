import json
from typing import Any

from core.ai.providers.base import BaseLLMProvider
from core.ai.agents.reversing_tools_definition import (
    build_reversing_tool_definitions,
    tool_call_finish,
    tool_call_finding,
    tool_calls_to_targets,
)


SYSTEM_PROMPT = """
You are a malware reverse-engineering analyst.

Analyze the current reversing evidence conservatively using symbols, assembly,
control flow and data flow.

Base follow-up investigation primarily on the current tool output and accumulated
reversing findings. Initialization context is guidance, not a reason to repeatedly
revisit the same artifacts.

Record findings when direct reversing evidence supports meaningful behavior.
Prefer exact address: instruction evidence.
A finding must represent meaningful behavior. Generic UI code, register setup,
stack manipulation or an unresolved call is normally context, not a finding.

Use native tools when additional evidence would materially improve the analysis.
Use the global investigation state to judge whether additional reversing is
likely to materially improve the result. Do not continue merely because tools
remain available. Do not stop merely because the current branch is exhausted if
the global investigation is still poorly covered.

Prefer following a strong concrete lead before continuing unrelated broad output.
Pending work is preserved and may be resumed later.

Discovery is candidate collection, not winner selection. Preserve multiple clearly
promising independent targets when useful and express preference through priority.

Do not call tools merely to keep the investigation moving.
Avoid work that has already been executed or is already pending.

When semantics remain unclear, prefer further evidence or a structural
interpretation over unsupported conclusions.
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
        Create a small initial investigation queue.

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
        Keep the initial queue focused. Do not call record_finding or
        finish_investigation during initial target selection.
        Put a short decision summary in message.content.
        """

        reversing_tool_definitions = build_reversing_tool_definitions(
            available_tools,
            include_finding_tools=False,
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
        enrichment: str,
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

        Global reversing context:
        {context_text}

        Enrichment context:
        {enrichment or "No enrichment is available."}

        Use native tool calls only. You may call record_finding when the evidence
        supports it and may call one or more investigation tools when useful.
        Use finish_investigation when no further local action is useful.
        Put a short decision summary in message.content.
        """

        reversing_tool_definitions = build_reversing_tool_definitions(
            available_tools,
            include_finding_tools=True,
        )

        response = self.llm.chat_tools(
            SYSTEM_PROMPT,
            prompt,
            reversing_tool_definitions,
        )

        finding = tool_call_finding(response.tool_calls)
        tool_calls = tool_calls_to_targets(
            response.tool_calls,
            priority=self._default_follow_up_priority(target),
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
            "finished": tool_call_finish(response.tool_calls),
            "finding": finding,
        }

    def _compact_target(self, target: dict[str, Any]) -> dict[str, Any]:
        return {
            "tool": target["tool"],
            "parameters": target["parameters"],
            "priority": target.get("priority"),
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
        summary = content.strip()
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

        if tool_call_finish(tool_calls):
            return "Model found no useful further local investigation for this branch."

        return "Model did not request additional reversing work for this chunk."

    def _default_follow_up_priority(self, target: dict[str, Any]) -> int:
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
