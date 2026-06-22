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
- After string_xrefs or import_xrefs returns code references, prefer function,
  disassembly, callers, or callees using an actual returned function/address.
- Avoid repeated related-string searches unless code evidence requires one.
- Return at most one concise finding and one next action.
- Use short analyst notes, not chain-of-thought.
- Return only JSON matching the supplied schema.
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
        prompt = f"""
        Analyze the observation and choose at most one next action.

        Current input target:
        {json.dumps(target, indent=2, ensure_ascii=False, default=str)}

        Tool executed:
        {target["tool"]}

        Tool output summary:
        {json.dumps(observation, indent=2, ensure_ascii=False, default=str)}

        Bounded raw tool chunk {chunk_index} of {total_chunks}:
        {json.dumps(chunk, indent=2, ensure_ascii=False, default=str)}

        Enrichment context:
        {enrichment or "No enrichment is available."}

        Available next actions:
        {json.dumps(available_tools, indent=2, ensure_ascii=False)}

        Choose:
        - action=none when this observation is not useful.
        - action=finish when investigation is sufficient.
        - a tool action only when more investigation is justified.

        For xref observations with code_targets, use one of those exact values for a
        function-oriented follow-up. Do not perform another string search when code can
        be followed directly.
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
