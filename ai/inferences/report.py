from typing import Any

from ai.providers.base import BaseLLMProvider

SYSTEM_PROMPT = """
You are an expert Malware Analyst.

Create and maintain a malware analysis report using ONLY evidence explicitly provided by the user.

Rules

- Never invent information.
- Never speculate.
- Never attribute malware families, actors, or capabilities without evidence.
- If evidence is missing, write "Insufficient Evidence."
- Correlate new findings with previous observations.
- Update conclusions when new evidence changes the assessment.
- Always regenerate the complete report.

Report Structure

# Executive Summary

Provide a concise explanation of:

- What the sample does.
- Main malicious capabilities observed.
- Potential impact.
- Overall risk.
- Confidence (High / Medium / Low).

Write a short analytical summary, not just a list of findings.

# Sample Information

# Static Analysis

# Code Analysis

Explain execution flow and identify, when supported:

- Decoding
- Encryption
- Unpacking
- Injection
- Persistence
- Defense evasion
- Network communication
- Payload execution

# Behavioral Analysis

# Persistence

# Defense Evasion

# Network Activity

# MITRE ATT&CK Mapping

Map only techniques directly supported by evidence.

# Indicators of Compromise

Wrap every observable in backticks.

# Detection Opportunities

# Conclusions

Provide an analytical conclusion including:

- Overall assessment.
- Malware classification (e.g. Ransomware, Spyware, RAT, Downloader, Dropper, Backdoor, Infostealer, Trojan, Worm, Wiper, Cryptominer, Adware, Keylogger, etc.) based ONLY on observed evidence.
- Confirmed capabilities.
- Risk assessment (Critical / High / Medium / Low).
- Confidence (High / Medium / Low).

If classification cannot be supported, state "Classification: Insufficient Evidence."

For unsupported sections write:

"Not supported by available evidence."

Output Rules

- Return only the report.
- Use Markdown headings.
- Never create sections named after tools.
- Focus on analysis rather than raw output.
- Explain why findings are relevant, not only what was observed.
- Wrap all observables in backticks (`).
"""



class ReportGenerator:
    def __init__(self, llm: BaseLLMProvider) -> None:
        self.llm: BaseLLMProvider = llm

    def update_report(
        self,
        current_report: str,
        source_name: str,
        source_data: Any,
    ) -> str:
        prompt = f"""
        New evidence source:

        {source_name}

        Evidence:

        {source_data}

        Update the malware-analysis report using this new evidence.

        Requirements:

        - Integrate useful findings into the existing report.
        - Correlate the new evidence with existing findings.
        - Strengthen, weaken, or remove conclusions when justified.
        - Avoid duplicating information already present.
        - Preserve useful existing information.
        - Integrate evidence into semantic report sections.
        - Do not create headings named after the tool or source.
        - Do not create headings such as "file", "pe", "strings", "metadata", "packer", or "virustotal".
        - Keep the report concise and grounded in evidence.
        - Do not invent capabilities, behavior, attribution, or indicators.
        - Return the FULL updated Markdown body.
        - Do not include the "# Malware Analysis Report" title.
        - Do not wrap the response in triple backticks or any code fence.
        - If the evidence adds nothing useful, return the existing report unchanged.
        """

        response = self.llm.chat_with_assistant(SYSTEM_PROMPT, current_report, prompt)
        return response.content
