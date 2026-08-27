import json
from typing import Any

from core.ai.providers.base import BaseLLMProvider
from core.ai.agents.reversing_tools_definition import (
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
- A reversing finding should contain at least one direct code evidence item
  whenever the finding was generated from disassembly.
- Direct code evidence must include the instruction address and instruction text.
- Static, dynamic, and enrichment context may support the interpretation, but
  must not replace direct code evidence in disassembly findings.
- After string_xrefs or import_xrefs returns code references, inspect an actual
  returned internal code address with disassembly instead of continuing with broad
  artifact searches.
- Request disassembly when target context, xrefs, imports, strings, callers,
  callees, or size make deeper assembly inspection useful.
- When disassembly shows a direct jump or call to another concrete internal code
  address, prefer a disassembly follow-up for that jump/call target
  to understand the next code path.
- When disassembly shows a direct call or jump to a concrete internal function
  such as fcn.00401230, you may request disassembly for that function to inspect
  its implementation, or callers for that function to understand who else reaches
  it. Choose the one that best answers the current investigation question.
- disassembly, callers, and callees accept only internal code addresses. Do not
  request them for imported APIs, Windows functions, or import thunks. Use
  import_xrefs for imports, then inspect a returned caller address when useful.
- Use callers when the inverse question is useful: who invokes this function, or
  whether the discovered function is reused by other code paths.
- Disassembly returns the complete selected function. Large disassembly output
  may be split into multiple chunks by the runtime; analyze each supplied chunk
  without requesting the same disassembly again just to continue reading it.
- Do not request disassembly for every function or for a simple import thunk,
  one-jump wrapper, or function with no meaningful instructions.
- Avoid repeated related-string searches unless code evidence requires one.
- Prefer one strong investigation path over several weak or speculative paths.
- Only propose follow-ups that are likely to reveal meaningful behavior or
  important code.
- Follow-ups should normally be derived from new evidence contained in the
  current tool result.
- Do not generate a follow-up only because a target appears in enrichment,
  investigation state, or previous context.
- Historical context should rank or interpret new evidence, not create
  unrelated follow-ups.
- Treat weak hypotheses as hints, not investigation objectives.
- If current hypotheses are weak or speculative and there is no concrete
  productive code path to verify them, prefer discovering new evidence rather
  than repeatedly trying to confirm them.
- Prefer actions that can produce genuinely new information about the sample.
- If a behavior is already sufficiently established, avoid repeatedly
  investigating the same evidence unless a new branch can materially expand
  understanding.
- When a promising code region is producing relevant internal calls or findings,
  prefer exploiting that branch before returning to generic discovery or
  repeated string searches.
- Do not use a function name by itself as behavior evidence. Use interesting
  names only as leads to inspect and verify the underlying code.
- Give priority to code related to encryption, file traversal, anti-analysis,
  persistence, payload loading, credential access, network/C2, and process
  execution.
- Use string_xrefs selectively. Do not investigate generic file extensions or
  common filename patterns in isolation, such as *.ini, *.txt, *.tmp, *.dll,
  *.exe, .ini, .txt, .tmp, .dll, or .exe. Follow extension strings only when
  they are unusual, campaign-specific, grouped with many target extensions, or
  tied to file enumeration, encryption, deletion, persistence, or configuration
  behavior.
- Before calling string_xrefs, prefer strings that can identify a specific
  behavior, configuration source, network endpoint, persistence mechanism,
  command, file target set, ransom note, mutex-like artifact, or malware-family
  artifact. Skip short fragments, boilerplate runtime text, and generic syntax
  unless stronger evidence makes them relevant.
- If the investigation has insufficient concrete targets or no enrichment is
  available, use focused discovery tools to inspect binary structure before
  guessing imports, strings, or addresses.
- Use list_imports when available APIs are unknown, list_functions when internal
  code candidates are needed, list_sections for binary layout, and
  list_entrypoints for additional execution starts.
- Discovery is a model decision. Choose one discovery tool only when it is the
  best next step; do not call every discovery tool mechanically.
- When processing discovery output, prioritize candidates contained in the
  current discovery result.
- Use previous findings, hypotheses, and enrichment only to rank or interpret
  candidates from the current discovery result.
- Do not ignore the current discovery result to repeat previously explored
  strings, imports, or targets unless the discovery output provides new
  evidence that justifies revisiting them.
- For list_functions, evaluate functions from the current chunk and decide
  whether one deserves disassembly, callers, callees, or another related action.
- For list_sections, evaluate returned sections and use inspect_section for an
  interesting section before pivoting to code, strings, or data.
- For list_imports, select relevant imports from the current result and use
  import_xrefs when that import is worth following.
- For list_entrypoints, evaluate returned entrypoints and use disassembly when
  one is worth inspecting.
- Do not call every discovery tool automatically. Do not repeat the same
  discovery tool without new evidence. Discovery results are context for
  selecting concrete follow-up targets, not instructions to inspect everything.
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

        thought = response.content.strip() or "Initial target selected by the model."
        targets = tool_calls_to_targets(
            response.tool_calls,
            priority=70,
        )

        return {
            "thought": thought,
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
        rejection_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        compact_target = self._compact_target(target)
        chunk_text = self._format_chunk_for_prompt(chunk)
        recovery_prompt = self._format_rejection_context(rejection_context)

        prompt = f"""
        Analyze this evidence chunk.

        Current input target:
        {json.dumps(compact_target, ensure_ascii=False, default=str)}

        Tool output summary:
        {json.dumps(observation, ensure_ascii=False, default=str)}

        Bounded raw tool chunk {chunk_index} of {total_chunks}:
        {chunk_text}

        Enrichment context:
        {enrichment or "No enrichment is available."}

        {recovery_prompt}

        Give the current tool output more weight than historical context.
        Generate candidates from the current tool output first, then use
        enrichment to prioritize or interpret them.
        Follow-ups should normally be derived from new evidence contained in the
        current tool result. Do not generate a follow-up only because a target
        appears in enrichment or previous context.
        Prefer one strong investigation path over several weak or speculative
        paths. Choose no follow-up when the current result does not provide a
        useful next step.
        Call record_finding only for evidence-backed malicious behaviour.
        Call at most one investigation tool when a follow-up is justified.
        If the current target is a discovery tool, choose the next action from
        candidates present in this discovery result unless there is a concrete
        new reason to revisit an older target.
        For xref observations with code_targets, choose disassembly using one of
        those exact addresses. For a disassembly jump or call to another concrete,
        behaviorally relevant internal address, choose disassembly for that target.
        For a disassembly call or jump to a concrete internal function such as
        fcn.00401230, choose either disassembly for that function or callers for
        that function. Use disassembly to inspect the implementation. Use callers
        to learn who else reaches it. Choose one.
        If this investigation line lacks concrete targets, use the single most
        useful discovery tool instead of speculative string/import guesses.
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

    def _native_thought(
        self,
        action: str,
    ) -> str:
        if action == "finish":
            return "The current investigation line is sufficient."
        if action == "none":
            return "No evidence-backed follow-up was selected."

        return f"Selected {action} from the current evidence."

    def _format_rejection_context(
        self,
        rejection_context: dict[str, Any] | None,
    ) -> str:
        if not isinstance(rejection_context, dict):
            return ""

        return f"""
        Previous requested action was rejected:
        {json.dumps(rejection_context, ensure_ascii=False, default=str)}

        The requested target is not valid or could not be resolved
        unambiguously for the selected tool. Use the available discovery or
        reference tools to resolve the target before retrying, choose another
        investigation path, or make no tool call if the path is not useful.
        """
