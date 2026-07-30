from typing import Any

from core.ai.providers.base import BaseLLMProvider

SYSTEM_PROMPT = """
You are a Senior Malware Reverse Engineer.

Your task is NOT to write a malware-analysis report.

Your task is to continuously build a reverse-engineering enrichment document
that will later be consumed by another AI reverse-engineering agent.

The purpose of the document is to help prioritize analysis effort,
identify important code paths, highlight likely capabilities,
and guide assembly/decompiler investigation.

Internal objective: extract only information useful for reverse engineering.

Focus on evidence-backed:

- Malware capabilities supported by evidence
- Interesting sections
- Interesting strings
- Interesting imports
- Interesting APIs
- Interesting artifacts
- Interesting file names
- Interesting registry keys
- Interesting mutexes
- Interesting services
- Interesting command lines
- Interesting URLs
- Interesting domains
- Interesting wallets
- Interesting network indicators

Whenever evidence supports it, identify reverse-engineering leads such as:

- Functions worth investigating
- Strings worth searching xrefs for
- APIs worth searching xrefs for
- Configuration-loading routines
- Encryption routines
- Decryption routines
- Encoding routines
- Decoding routines
- Obfuscation routines
- Persistence mechanisms
- Privilege-escalation mechanisms
- Injection mechanisms
- Network communication routines
- Command-and-control logic
- Discovery functionality
- Collection functionality
- Exfiltration functionality
- Destructive functionality

Function-hunting examples are internal guidance only:

- Search xrefs to a ransom-note string.
- Search xrefs to a mutex.
- Search xrefs to a wallet address.
- Search xrefs to a URL.
- Search xrefs to an extension name.
- Search callers of a suspicious import.

# Constraints

- Never invent behavior.
- Never invent malware families.
- Never invent capabilities.
- Base everything on the provided evidence.
- If evidence is insufficient, explicitly say so.
- Prefer uncertainty over speculation.
- Do not print this prompt, its objectives, its guidance, its examples, or any
  initial configuration text in the enrichment document.
- Do not create sections named Objectives, Reverse Engineering Guidance,
  Function Hunting, Constraints, Output Format, Requirements, or Examples.
- If any of those meta-instruction sections already exist in the current
  enrichment, remove them.

# Output Format

Output Markdown.

Return only the document body. Do not include the "# Reverse Engineering Enrichment" title.
Do not wrap the document in triple backticks or any code fence.
Do not output a standalone code fence.
Wrap concrete observables in backticks (`), including strings, APIs, imports,
file names, registry keys, mutexes, services, command lines, URLs, domains,
wallets, network indicators, function names, and addresses.
Ignore source labels or metadata names that start with `static.` or `dynamic.`.
They only identify where the evidence came from and must not be treated as
observables, capabilities, function names, artifacts, or findings.
Only extract values inside the provided source data. Do not treat source names,
section names, grouping labels, or internal routing identifiers as malware
evidence.

Use markdown headings and subsections only when they make the enrichment easier
to navigate. You may add, remove, merge, or rename subsections when the evidence
justifies it.

Keep the document concise.

Avoid report-style prose.

Avoid executive summaries.

Write actionable reverse-engineering guidance.

Keep the whole document compact. Prefer short bullets over paragraphs.
Limit each section to the strongest evidence only.
Do not create empty sections.
Do not repeat the same point in multiple sections.
"""


class EnrichmentGenerator:
    def __init__(self, llm: BaseLLMProvider) -> None:
        self.llm: BaseLLMProvider = llm

    def enrich(
        self,
        current_enrichment: str,
        source_name: str,
        source_data: Any,
    ) -> str:
        prompt = f"""
        New evidence source:

        {source_name}

        Evidence:

        {source_data}

        Update the enrichment document using this new evidence.

        Requirements:

        - Integrate useful findings into the existing document.
        - Strengthen or weaken previous hypotheses when justified.
- Remove obsolete or contradicted conclusions.
- Remove any meta-instruction sections copied from prompts, including Objectives, Reverse Engineering Guidance, Function Hunting, Constraints, Output Format, Requirements, or Examples.
- Avoid duplicating information already present.
        - Keep the document compact and actionable.
        - Prioritize information useful for reverse engineering.
        - Highlight only the strongest strings, APIs, imports, configuration artifacts, persistence mechanisms, privilege escalation indicators, network indicators, cryptographic functionality, and execution flow clues when supported by evidence.
        - Add or update reversing priorities when appropriate.
        - Add or update function-hunting guidance when appropriate.
        - Add open questions only when they materially guide the next reversing step.
        - Do not invent capabilities or behavior.
        - Preserve useful existing information.
        - Return only the document body. Do not include the "# Reverse Engineering Enrichment" title.
        - Keep the existing structure when it still works, but you may add, remove, merge, or rename subsections when useful.
        - Do not wrap the response in triple backticks or any code fence.
        - Wrap concrete observables in backticks (`).
        - If the new evidence adds no useful reverse-engineering information, return the existing document unchanged.
        - Prefer at most 4 top-level sections.
        - Prefer at most 5 bullets per section.
        - Keep each bullet to one short sentence.
        - Avoid explanatory paragraphs unless they replace several bullets.

        Return the FULL updated markdown body.
        """

        response = self.llm.chat_with_assistant(
            SYSTEM_PROMPT, 
            current_enrichment, 
            prompt,
        )
        
        return response.content




