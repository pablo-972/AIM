import json
from typing import Any

from ai.providers.base import BaseLLMProvider
from ai.schemas.dynamic import DYNAMIC_INFERENCE_FINDING_SCHEMA
from ai.schemas.parsing import parse_dynamic_inference_finding

SYSTEM_PROMPT = """
# Role
You are an expert malware dynamic-analysis classifier.

# Objective
Inspect one small dynamic-analysis evidence chunk and decide whether it shows
malware-relevant behavior.

# Evidence Types
- Procmon section chunks contain raw normalized events grouped by behavior.
- Autoruns and registry chunks contain only before/after differences.
- Procmon chunks may contain only a representative subset of a larger section.
  Use total_items, selected_items, truncated, and selection_strategy to
  understand coverage. Do not claim that no other behavior occurred outside the
  provided chunk.

# What To Report
Report a finding only for concrete behavior supported by the evidence:
- persistence or autorun changes
- suspicious registry changes
- file creation, modification, deletion, or rename behavior
- process creation, termination, or notable image loading
- DNS, TCP, or UDP network activity
- ransomware-style activity such as ransom note creation, many file writes,
  renames, deletes, or recovery/safety-control tampering

# Diffing Rule
For Autoruns and registry evidence, compare before and after values. Report only
if the difference is behaviorally relevant. Do not report unchanged data.

# Output
Return ONLY valid JSON matching the provided schema.
If there is relevant behavior, return finding with:
- category: concise label such as "file_creation", "network_connection",
  "autorun_persistence", "registry_persistence", "registry_modification",
  "process_execution", "file_modification", "file_deletion", or "file_rename".
- tone: concise behavior label such as "persistence", "network", "filesystem",
  "process", "registry", "ransomware", or "unknown".
- explanation: a brief plain-language explanation of what the behavior means
  and why the evidence supports it. Mention concrete evidence such as the file,
  registry key, process, or network endpoint when available.

If the evidence is not relevant, return finding=null.
The "thought" field must be a short operational summary, maximum 1 sentence.
Do not include chain-of-thought or step-by-step reasoning.
"""

SECTION_HINTS = {
    "processes.created": "Look for child process execution and suspicious command lines.",
    "processes.terminated": "Look for attempts to stop tools, services, or security processes.",
    "processes.loaded_images": "Look for notable DLL/image loads related to injection or abuse.",
    "filesystem.created": "Look for created files or directories, especially ransom notes, dropped binaries, scripts, or startup paths.",
    "filesystem.modified": "Look for content writes or metadata changes that suggest encryption, tampering, or payload staging.",
    "filesystem.deleted": "Look for destructive deletes or cleanup behavior.",
    "filesystem.renamed": "Look for ransomware-style renames or extension changes.",
    "registry.created": "Look for registry key creation that suggests persistence or configuration changes.",
    "registry.modified": "Look for registry value changes that suggest persistence, execution, or security tampering.",
    "registry.deleted": "Look for deletion of registry keys or values.",
    "network.dns": "Look for DNS transport or domain lookup behavior.",
    "network.tcp": "Look for outbound TCP connections or reconnect attempts to remote infrastructure.",
    "network.udp": "Look for UDP traffic to remote infrastructure.",
}


class DynamicInference:
    def __init__(self, llm: BaseLLMProvider) -> None:
        self.llm: BaseLLMProvider = llm

    def analyze_chunk(self, input_ref: dict[str, Any]) -> dict[str, Any]:
        prompt = self._prompt(input_ref)

        response = self.llm.chat_json(
            SYSTEM_PROMPT, 
            prompt, 
            DYNAMIC_INFERENCE_FINDING_SCHEMA,
        )

        dynamic_findigs = parse_dynamic_inference_finding(response.content)
        return dynamic_findigs


    def _prompt(self, input_ref: dict[str, Any]) -> str:
        tool = input_ref.get("tool", "unknown")
        section = input_ref.get("section", "unknown")
        evidence = input_ref.get("value")
        hint = self._hint(tool, section)
        coverage = self._coverage(input_ref)

        return f"""
        Task:
        Inspect this dynamic-analysis evidence chunk. Decide if it contains one
        malware-relevant finding. If it does not, return finding=null.
        If it does, explain the concrete behavior in finding.explanation.

        Tool: {tool}
        Section: {section}
        Focus: {hint}
        Coverage:
        {json.dumps(coverage, ensure_ascii=False, default=str)}

        Evidence:
        {json.dumps(evidence, ensure_ascii=False, default=str)}
        """

    def _hint(self, tool: str, section: str) -> str:
        if tool == "autoruns":
            return "Compare before/after autorun entries and look for persistence changes."

        if tool == "registry":
            return "Compare before/after registry values and look for persistence, execution, or security-impacting changes."

        return SECTION_HINTS.get(
            section, 
            "Look only for concrete behavior supported by this evidence.",
        )

    def _coverage(self, input_ref: dict[str, Any]) -> dict[str, Any]:
        coverage_fields = (
            "total_items",
            "selected_items",
            "truncated",
            "selection_strategy",
        )
        coverage = {}

        for field in coverage_fields:
            if field in input_ref:
                coverage[field] = input_ref.get(field)

        return coverage or {"type": "complete_or_not_provided"}
