import json
from typing import Any

from ai.providers.base import BaseLLMProvider
from ai.schemas.parsing import parse_json_object
from ai.schemas.reversing import (
    REVERSING_ACTION_NAMES,
    REVERSING_ANALYSIS_SCHEMA,
    REVERSING_SEED_SCHEMA,
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
- Create critical_code_region findings only when xref, function, caller/callee,
  or disassembly evidence ties the behavior to code.
- After string_xrefs or import_xrefs returns code references, inspect an actual
  returned function/address instead of continuing with broad artifact searches.
- Use function as a lightweight first inspection after xrefs.
- Request disassembly when the inspected function contains concrete suspicious
  instructions, calls, control flow, loops, API use, or data manipulation that
  warrants deeper assembly analysis.
- Do not request disassembly for every function or for a simple import thunk,
  one-jump wrapper, or function with no meaningful instructions.
- Avoid repeated related-string searches unless code evidence requires one.
- Return at most one concise finding and one next action.
- Use short analyst notes, not chain-of-thought.
- Return only JSON matching the supplied schema.
"""
MAX_EVIDENCE_ENRICHMENT_LENGTH = 3500
MAX_TARGET_REASON_LENGTH = 500


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

        Available tools:
        {json.dumps(available_tools, indent=2, ensure_ascii=False)}

        Prioritize targets that can lead to critical code regions:
        - suspicious imports with import_xrefs
        - behaviorally meaningful strings with string_xrefs
        - concrete functions with function or disassembly

        Do not prioritize wallet, payment, contact, Session, or onion strings unless
        they are needed to locate ransom-note generation code. Do not invent addresses.
        Return no more than six targets.
        """
        
        response = self.llm.chat_json(
            SYSTEM_PROMPT,
            prompt,
            REVERSING_SEED_SCHEMA,
        )
        result = parse_json_object(response.content, fallback={})
        if not isinstance(result.get("targets"), list):
            raise ValueError("Invalid reversing seed response.")
        return result

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
        bounded_enrichment = self._bounded_text(
            enrichment,
            MAX_EVIDENCE_ENRICHMENT_LENGTH,
        )
        compact_target = {
            "tool": target["tool"],
            "parameters": target["parameters"],
            "priority": target.get("priority"),
            "reason": self._bounded_text(
                str(target.get("reason") or ""),
                MAX_TARGET_REASON_LENGTH,
            ),
        }
        compact_tools = {
            name: {
                "parameters": list(spec.get("parameters", {})),
            }
            for name, spec in available_tools.items()
            if isinstance(spec, dict)
        }
        prompt = f"""
        Analyze the observation and choose at most one next action.

        Current input target:
        {json.dumps(compact_target, ensure_ascii=False, default=str)}

        Tool executed:
        {target["tool"]}

        Tool output summary:
        {json.dumps(observation, ensure_ascii=False, default=str)}

        Bounded raw tool chunk {chunk_index} of {total_chunks}:
        {json.dumps(chunk, ensure_ascii=False, default=str)}

        Bounded enrichment context:
        {bounded_enrichment or "No enrichment is available."}

        Available next actions:
        {json.dumps(compact_tools, ensure_ascii=False)}

        Choose:
        - action=none when this observation is not useful.
        - action=finish when investigation is sufficient.
        - a tool action only when more investigation is justified.

        For xref observations with code_targets, use one of those exact values for a
        function-oriented follow-up. Inspect it with function first. If the current
        target is already a function, choose disassembly only when its instructions
        provide concrete evidence that deeper assembly analysis is valuable.
        """

        response = self.llm.chat_json(
            SYSTEM_PROMPT,
            prompt,
            REVERSING_ANALYSIS_SCHEMA,
        )
        result = parse_json_object(response.content, fallback={})
        required = {"thought", "confidence", "action", "parameters", "finding"}
        
        if not required.issubset(result):
            raise ValueError("Invalid reversing evidence response.")
        if result["action"] not in REVERSING_ACTION_NAMES:
            raise ValueError("Invalid reversing action.")
        if result["confidence"] not in {"low", "medium", "high"}:
            raise ValueError("Invalid reversing confidence.")
        if not isinstance(result["parameters"], dict):
            raise ValueError("Invalid reversing parameters.")
        if result["finding"] is not None and not isinstance(
            result["finding"],
            dict,
        ):
            raise ValueError("Invalid reversing finding.")
        return result

    def _bounded_text(self, value: str, limit: int) -> str:
        if len(value) <= limit:
            return value

        half = limit // 2
        return f"{value[:half]}\n...[truncated]...\n{value[-half:]}"
