import json
from typing import Any

from core.ai.providers.base import BaseLLMProvider
from core.ai.schemas.dynamic import DYNAMIC_INFERENCE_FINDING_SCHEMA
from core.ai.schemas.parsing import parse_dynamic_inference_finding

SYSTEM_PROMPT = """
# Role
You are an expert malware dynamic-analysis classifier.

# Objective
Inspect one selected dynamic-analysis evidence section and decide whether it shows
malware-relevant behavior.

# Evidence Types
- Procmon sections contain selected normalized events grouped by behavior.
- Procmon collection groups summarize the whole selected artifact section. When
  a collection has truncated=true or total_items is larger than selected_count,
  inspect groups before items because groups may expose the dominant behavior.
- Autoruns and registry sections contain only before/after differences.
- Procmon sections may contain only selected items from a larger artifact.
  Use index, total_chunks, total_items, and selected_count to understand what
  part of the section was provided. Do not claim that no other behavior occurred
  outside the provided evidence.

# What To Report
Report a finding only for concrete behavior supported by the evidence:
- persistence or autorun changes
- suspicious registry changes
- file creation, modification, deletion, or rename behavior
- process creation, termination, or notable image loading
- DNS, TCP, or UDP network activity, including connection attempts,
  reconnect attempts, accepts, sends, receives, disconnects, and repeated
  remote endpoint activity. Do not require a confirmed established session
  before reporting suspicious network behavior.
- ransomware-style activity such as ransom note creation, many file writes,
  renames, deletes, or recovery/safety-control tampering

# Diffing Rule
For Autoruns and registry evidence, compare before and after values. Report only
if the difference is behaviorally relevant. Do not report unchanged data.

# Deduplication Rule
Use the existing finding explanations as memory of behavior already reported.
Do not emit another finding when the current evidence describes the same
behavior, impact, and evidence pattern as an existing finding. Prefer returning
finding=null over repeating a finding with different wording.

# Output
Return ONLY valid JSON matching the provided schema.
If there is relevant behavior, return finding with:
- category: concise label such as "file_creation", "network_connection",
  "network_attempt", "network_reconnect", "network_transfer",
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
    "processes.created": "Look for child process execution and suspicious command lines. Use both process and command_line when present.",
    "processes.terminated": "Look for attempts to stop tools, services, or security processes.",
    "processes.loaded_images": "Look for notable DLL/image loads that suggest capabilities such as cryptography, networking, injection, scripting, compression, or system manipulation.",
    "filesystem.created": "Look for created files or directories, especially repeated filenames or groups such as ransom notes, dropped binaries, scripts, or startup paths.",
    "filesystem.modified": "Look for content writes or metadata changes that suggest encryption, tampering, or payload staging.",
    "filesystem.deleted": "Look for destructive deletes or cleanup behavior.",
    "filesystem.renamed": "Look for suspicious rename behavior, especially destination_extension or extension_transition groups, hidden or staged paths, misleading names, repeated renames, or possible ransom/encryption activity.",
    "registry.created": "Look for registry key creation that suggests persistence or configuration changes.",
    "registry.modified": "Look for registry value changes that suggest persistence, execution, or security tampering.",
    "registry.deleted": "Look for deletion of registry keys or values.",
    "network.connections": "Look for any network activity involving remote infrastructure: connection attempts, reconnect attempts, accepts, sends, receives, disconnects, repeated remote endpoints, ports, and transfer patterns. Reconnect-only activity is still relevant evidence of attempted communication.",
    "network.dns": "Look for DNS transport activity. Do not infer queried domains when the evidence only contains DNS server transport.",
}

class DynamicInference:
    def __init__(self, llm: BaseLLMProvider) -> None:
        self.llm: BaseLLMProvider = llm

    def analyze_section(
        self,
        input_ref: dict[str, Any],
        existing_explanations: list[str] | None = None,
    ) -> dict[str, Any]:
        prompt = self._prompt(input_ref, existing_explanations or [])

        response = self.llm.chat_json(
            SYSTEM_PROMPT, 
            prompt, 
            DYNAMIC_INFERENCE_FINDING_SCHEMA,
        )

        dynamic_findigs = parse_dynamic_inference_finding(response.content)
        return dynamic_findigs


    def _prompt(
        self,
        input_ref: dict[str, Any],
        existing_explanations: list[str],
    ) -> str:
        tool = input_ref.get("tool", "unknown")
        section = input_ref.get("section", "unknown")
        evidence = input_ref.get("value")
        hint = self._hint(tool, section)
        coverage = self._coverage(input_ref)

        return f"""
        Task:
        Inspect this selected dynamic-analysis evidence section. Decide if it contains one
        malware-relevant finding. If it does not, return finding=null.
        If it does, explain the concrete behavior in finding.explanation.

        Tool: {tool}
        Section: {section}
        Focus: {hint}
        Selection:
        {json.dumps(coverage, ensure_ascii=False, default=str)}

        Existing finding explanations:
        {json.dumps(existing_explanations, ensure_ascii=False, default=str)}

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
            "index",
            "total_chunks",
            "total_items",
            "selected_count",
        )
        coverage = {}

        for field in coverage_fields:
            if field in input_ref:
                coverage[field] = input_ref.get(field)

        return coverage or {"type": "not_provided"}
