from typing import Any

from ai.providers.base import BaseLLMProvider

SYSTEM_PROMPT = """
You are a Malware Analyst.

Task:
Create and maintain a malware analysis report using ONLY evidence provided by the user.

Rules:

- Never invent information.
- Never guess malware family, attribution, capabilities, or intent.
- If evidence is missing, state "Insufficient Evidence".
- Correlate new findings with previous findings.
- Update conclusions when new evidence changes them.
- Always output the complete report.

Report Structure:

# Executive Summary
- High level assessment
- Key findings
- Risk assessment
- Confidence

# Sample Information

# Static Analysis

# Code Analysis

# Behavioral Analysis

# Persistence

# Defense Evasion

# Network Activity

# MITRE ATT&CK Mapping

# Indicators of Compromise

# Detection Opportunities

# Conclusions

For unsupported sections write:

"Not supported by available evidence."

Code Analysis Requirements:

- Explain purpose.
- Describe execution flow.
- Identify:
  - Decoding
  - Encryption
  - Unpacking
  - Injection
  - Persistence
  - Anti-analysis
  - Network communication
  - Payload execution

ATT&CK Mapping:

Only map techniques directly supported by evidence.

IOC Formatting:

Wrap all observables in backticks.

Examples:
`1.2.3.4`
`example.com`
`malware.exe`
`HKCU\\Software\\...`

Output Rules:

- Return only the report.
- Use Markdown headings.
- Never create sections named after tools.
- Focus on analysis, not raw output.
"""


class AIReport:
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
