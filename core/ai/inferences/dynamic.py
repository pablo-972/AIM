import json
from typing import Any

from core.ai.providers.base import BaseLLMProvider
from core.ai.schemas.dynamic import (
    DYNAMIC_INFERENCE_FINDING_SCHEMA,
    parse_dynamic_inference_finding,
)

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

Create a finding whenever the observed evidence provides malware-analysis-relevant
behavior, capability, artifact, or system interaction.

A finding does not need to prove malicious intent by itself.

Relevant examples include:
- cryptographic or networking libraries loaded;
- file creation, modification, deletion or renaming;
- process creation and command execution;
- registry modification;
- network communication;
- security-control interaction;
- persistence-related artifacts;
- system reconnaissance.

Use confidence to express how strongly the evidence supports a malware-relevant
interpretation.

Do not suppress a relevant finding merely because the behavior may also occur in
legitimate software.

# Diffing Rule
For Autoruns and registry evidence, compare before and after values. Report only
if the difference is behaviorally relevant. Do not report unchanged data.

# Network Rule
For Procmon network.connections evidence, any non-empty network activity from
the sample is relevant by default. Report a network finding for observed remote
endpoints, connection attempts, reconnect attempts, accepts, sends, receives,
disconnects, or repeated endpoint activity. Do not require the endpoint to be
known malicious, and do not require confirmed connected=true.

# Deduplication Rule
Use the existing finding summaries as memory of behavior already reported.
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
- summary: a brief plain-language summary of what the behavior means and why
  the evidence supports it. Mention concrete evidence such as the file,
  registry key, process, or network endpoint when available.
- evidence: a list of short concrete observations from the supplied dynamic
  evidence that directly support the finding.

When producing a finding, include only the minimal concrete events from the
supplied dynamic evidence that directly support the finding.
Each evidence item must be a string representing one observed fact.
Use short strings such as:
- "Loaded C:\\Windows\\System32\\crypt32.dll"
- "cmd.exe executed: cmd /C net session"
- "Created C:\\Users\\Public\\payload.exe"
- "TCP connection to www.server-q01.com:443"
Do not copy the complete input section or chunk.
Do not include unrelated surrounding events.
Do not include context, metadata, counters, complete data blocks, groups, items,
source, section, index, total_chunks, total_items, or selected_count inside
evidence.
Source information is stored separately and must not be duplicated in evidence.
Evidence must be grounded in the supplied dynamic data.
Preserve exact paths, command lines, process names, registry keys, domains,
addresses, ports, protocols, or other concrete values when they are relevant.
Do not serialize JSON objects, arrays, key=value blocks, full chunks, context,
or data inside evidence.
Do not add conclusions or hypotheses inside evidence; interpretation belongs in
summary.

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
    "network.connections": "Treat any non-empty network activity as relevant. Report observed remote endpoints, connection attempts, reconnect attempts, accepts, sends, receives, disconnects, repeated endpoints, ports, and transfer patterns. Reconnect-only activity is still relevant evidence of attempted communication.",
    "network.dns": "Look for DNS transport activity. Do not infer queried domains when the evidence only contains DNS server transport.",
}

class DynamicInference:
    def __init__(self, llm: BaseLLMProvider) -> None:
        self.llm: BaseLLMProvider = llm

    def analyze_section(
        self,
        input_ref: dict[str, Any],
        existing_summaries: list[str] | None = None,
    ) -> dict[str, Any]:
        prompt = self._prompt(input_ref, existing_summaries or [])

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
        existing_summaries: list[str],
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
        If it does, summarize the concrete behavior in finding.summary and
        include only short concrete observations in finding.evidence.

        Tool: {tool}
        Section: {section}
        Focus: {hint}
        Selection:
        {json.dumps(coverage, ensure_ascii=False, default=str)}

        Existing finding summaries:
        {json.dumps(existing_summaries, ensure_ascii=False, default=str)}

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
