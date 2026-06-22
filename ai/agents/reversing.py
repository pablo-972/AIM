import json
from typing import Any

from ai.providers.base import BaseLLMProvider
from ai.schemas.parsing import parse_json_object
from ai.schemas.reversing import (
    REVERSING_ANALYSIS_SCHEMA,
    REVERSING_SEED_SCHEMA,
)


SYSTEM_PROMPT = """
You are a malware reverse-engineering agent.

Choose concrete investigation targets and analyze tool evidence. Stay grounded
in the supplied enrichment and tool output. Never invent behavior, functions,
imports, strings, addresses, or findings.

Higher target priority means it should be investigated sooner.

When analyzing evidence:
- Mark it relevant only when it explains malware behavior or guides further
  reverse engineering.
- Return at most one concise, evidence-backed finding per chunk.
- Suggest only concrete follow-up targets justified by current evidence.
- Prefer xrefs, callers, callees, and bounded disassembly.
- Set finish=true only when the current evidence indicates there are no useful
  follow-up targets.

The thought field must be a short operational summary, not chain-of-thought.
Return only JSON matching the supplied schema.
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
        Create the initial reverse-engineering investigation queue.

        Existing enrichment:
        {enrichment or "No enrichment is available."}

        Bounded reconnaissance:
        {json.dumps(reconnaissance, indent=2, ensure_ascii=False, default=str)}

        Available tools:
        {json.dumps(available_tools, indent=2, ensure_ascii=False)}

        Choose a small set of high-value targets from interesting strings, suspicious
        imports, and large or suspicious functions.
        """
        
        response = self.llm.chat_json(
            SYSTEM_PROMPT,
            prompt,
            REVERSING_SEED_SCHEMA,
        )
        return parse_json_object(
            response.content,
            fallback={
                "reasoning": "No initial targets returned.",
                "targets": [],
            },
        )


    def analyze_evidence(
        self,
        enrichment: str,
        target: dict[str, Any],
        chunk: Any,
        chunk_index: int,
        total_chunks: int,
        available_tools: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = f"""
        Analyze one chunk returned for the current investigation target.

        Existing enrichment:
        {enrichment or "No enrichment is available."}

        Current target:
        {json.dumps(target, indent=2, ensure_ascii=False, default=str)}

        Tool evidence chunk {chunk_index} of {total_chunks}:
        {json.dumps(chunk, indent=2, ensure_ascii=False, default=str)}

        Available tools for follow-up:
        {json.dumps(available_tools, indent=2, ensure_ascii=False)}
        """
        
        response = self.llm.chat_json(
            SYSTEM_PROMPT,
            prompt,
            REVERSING_ANALYSIS_SCHEMA,
        )
        return parse_json_object(
            response.content,
            fallback={
                "relevant": False,
                "thought": "No valid evidence decision returned.",
                "confidence": "low",
                "finding": None,
                "next_targets": [],
                "finish": False,
            },
        )
