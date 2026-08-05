import json
from typing import Any

from core.ai.providers.base import BaseLLMProvider
from core.ai.agents.reversing_tools import (
    build_reversing_tool_definitions,
    tool_call_action,
    tool_call_finding,
    tool_calls_to_targets,
)


SYSTEM_PROMPT = """
You are a malware reverse-engineering agent.

Main objective:
Identify critical assembly and code regions associated with malicious behavior.
Assembly evidence is the primary source of truth. Enrichment, strings, and
imports are only pivots used to reach executable code.

Critical regions include code related to ransom-note generation, file traversal,
file encryption, extension modification, cryptographic routines, process
execution, defense evasion, shadow-copy deletion, privilege escalation,
persistence, network communication, API resolution, and anti-analysis.

Rules:
- Stay grounded in the supplied tool observation.
- Never invent functions, addresses, instructions, imports, xrefs, or behavior.
- Never contradict numeric observation fields.
- If matches_count is greater than zero, do not claim there were no matches.
- If returned_instructions is zero, do not claim code was analyzed.
- Plain wallet, payment, contact, Session, or onion strings are artifacts. They
  are not configuration loading or C2 without code evidence.
- Create critical_code_region findings only when xref, caller/callee,
  or disassembly evidence ties the behavior to code.
- After string_xrefs or import_xrefs returns code references, inspect an actual
  returned internal code address with disassembly instead of continuing with broad
  artifact searches.
- Request disassembly when target context, xrefs, imports, strings, callers,
  callees, or size make deeper assembly inspection useful.
- When disassembly shows a direct jump or call to another concrete internal code
  address, prefer a disassembly follow-up for that jump/call target
  to understand the next code path.
- disassembly, callers, and callees accept only internal code addresses. Do not
  request them for imported APIs, Windows functions, or import thunks. Use
  import_xrefs for imports, then inspect a returned caller address when useful.
- Do not use callers merely because the current function jumps or calls another
  function. Callers answers the inverse question: who invokes this function.
- Disassembly returns the complete selected function. Large disassembly output
  may be split into multiple chunks by the runtime; analyze each supplied chunk
  without requesting the same disassembly again just to continue reading it.
- Do not request disassembly for every function or for a simple import thunk,
  one-jump wrapper, or function with no meaningful instructions.
- Avoid repeated related-string searches unless code evidence requires one.
- Use tool calls for findings and next actions.
- You may record one concise finding and request one next investigation tool.
- Use short analyst notes, not chain-of-thought.
- Do not invent tool arguments.
"""

class ReversingAgent:
    def __init__(self, llm: BaseLLMProvider) -> None:
        self.llm = llm

    def create_initial_targets(
        self,
        enrichment: str,
        reconnaissance: dict[str, Any],
        available_tools: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = f"""
        Create a small initial investigation queue.

        Enrichment context:
        {enrichment or "No enrichment is available."}

        Bounded reconnaissance:
        {json.dumps(reconnaissance, indent=2, ensure_ascii=False, default=str)}

        Prioritize targets that can lead to critical code regions:
        - suspicious imports with import_xrefs
        - behaviorally meaningful strings with string_xrefs
        - concrete internal code addresses with disassembly

        Do not prioritize wallet, payment, contact, Session, or onion strings unless
        they are needed to locate ransom-note generation code. Do not invent addresses.
        Make no more than six investigation tool calls. Do not call record_finding or
        finish_investigation during initial target selection.
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

        reason = response.content.strip() or "Initial target selected by the model."
        targets = tool_calls_to_targets(
            response.tool_calls,
            priority=70,
            reason=reason,
        )

        return {
            "reasoning": reason,
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
    ) -> dict[str, Any]:
        compact_target = self._compact_target(target)

        prompt = f"""
        Analyze this evidence chunk.

        Current input target:
        {json.dumps(compact_target, ensure_ascii=False, default=str)}

        Tool output summary:
        {json.dumps(observation, ensure_ascii=False, default=str)}

        Bounded raw tool chunk {chunk_index} of {total_chunks}:
        {json.dumps(chunk, ensure_ascii=False, default=str)}

        Enrichment context:
        {enrichment or "No enrichment is available."}

        Call record_finding only for evidence-backed malicious behaviour.
        Call at most one investigation tool when a follow-up is justified.
        For xref observations with code_targets, choose disassembly using one of
        those exact addresses. For a disassembly jump or call to another concrete,
        behaviorally relevant internal address, choose disassembly for that target.
        Do not request the same disassembly merely to continue reading
        its chunks. Call finish_investigation when this line of investigation is
        sufficient. Make no tool call when the observation is not useful.
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

        action, parameters = tool_call_action(response.tool_calls)
        thought = response.content.strip() or self._native_thought(action)
        finding = tool_call_finding(response.tool_calls)
        confidence = "medium"
        if isinstance(finding, dict) and finding.get("confidence") in {
            "low",
            "medium",
            "high",
        }:
            confidence = finding["confidence"]

        return {
            "thought": thought,
            "confidence": confidence,
            "action": action,
            "parameters": parameters,
            "finding": finding,
        }

    def _compact_target(self, target: dict[str, Any]) -> dict[str, Any]:
        return {
            "tool": target["tool"],
            "parameters": target["parameters"],
            "priority": target.get("priority"),
            "reason": str(target.get("reason") or ""),
        }

    def _native_thought(
        self,
        action: str,
    ) -> str:
        if action == "finish":
            return "The current investigation line is sufficient."
        if action == "none":
            return "No evidence-backed follow-up was selected."

        return f"Selected {action} from the current evidence."
