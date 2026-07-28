import json
from json import JSONDecodeError
from dataclasses import dataclass
from typing import Any

from core.ai.providers.base import BaseLLMProvider
from core.ai.schemas.report import REPORT_SCHEMA, parse_report_result


MAX_REPORT_ATTEMPTS = 2

REPORT_UPDATE_SYSTEM_PROMPT = """
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
- Return Markdown only.
- Do not return JSON.
- Do not include any machine-readable assessment object.
- Wrap all observables in backticks (`).
"""

REPORT_FINAL_SYSTEM_PROMPT = """
You are an expert Malware Analyst.

Generate a complete malware analysis report using only the supplied static,
dynamic and reverse-engineering evidence.

Return the response according to the provided JSON schema.

The report_markdown field must contain the complete report in Markdown.

The assessment object must contain the final machine-readable verdict.

Determine independently:

- Whether the sample is malicious.
- Confidence in the malicious or benign verdict.
- The most likely concrete malware family or malicious tool.
- Confidence in that family or tool attribution.
- The applicable behavioural categories.

malware_confidence represents the model's estimated confidence that the sample
is malicious. It is not a calibrated statistical probability.

family_confidence represents confidence in the concrete malware family or
malicious tool stored in the family field. It must not represent general
confidence that the sample is malicious.

If the available evidence is insufficient for concrete family or tool
attribution, set family to null and assign a low family_confidence value.

Do not force a family or tool attribution.
Do not identify a concrete malware family solely from generic behaviours shared
by many families.
Do not invent evidence, behaviours, functions, APIs, strings, addresses,
indicators or findings.
All conclusions must be supported by the supplied analysis data.
Keep summary_reason concise and focused on the strongest evidence.
Do not place the raw assessment JSON inside report_markdown.

When a JSON schema is supplied by the caller, the schema overrides the free-form
Markdown output rule. In that case, return one JSON object matching the schema.
"""


@dataclass(frozen=True)
class GeneratedReport:
    report_markdown: str
    assessment: dict[str, Any]


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

        response = self.llm.chat_with_assistant(
            REPORT_UPDATE_SYSTEM_PROMPT, 
            current_report, 
            prompt,
        )
        
        return self._extract_markdown_update(response.content)

    def finalize_report(self, current_report: str) -> GeneratedReport:
        prompt = """
        Convert the current malware-analysis report into the required structured
        output.

        Requirements:

        - Keep report_markdown as the complete analyst-facing Markdown report.
        - Include a Final Assessment section in report_markdown.
        - Do not include the raw assessment JSON inside report_markdown.
        - Fill assessment with the final machine-readable verdict.
        - Fill every assessment field required by the schema.
        - Use only evidence already present in the current report.

        Assessment field guide:

        - is_malware: true if the report supports malicious behavior, otherwise false.
        - malware_confidence: confidence from 0 to 1 for the malicious or benign verdict.
        - family: the name of a concrete malware family or malicious tool identifiable from code, behavior, artifacts, or a known name. Valid examples include AgentTesla, Emotet, TrickBot, QakBot, RedLine, AsyncRAT, LockBit, and DarkGate. Set family to null when only a broad type is supported.
        - family_confidence: confidence from 0 to 1 for the value selected in family.
        - categories: malware types, objectives, or main capabilities supported by evidence. Use labels such as ransomware, credential_stealer, information_stealer, keylogger, remote_access_trojan, downloader, dropper, backdoor, spyware, bot, banking_trojan, wiper, cryptominer, loader, persistence, encryption, network_communication, defense_evasion, file_modification, or registry_modification. Do not put concrete family/tool names here.
        - summary_reason: one short explanation of the strongest evidence behind the verdict and classification.
        """

        last_error: Exception | None = None
        
        for attempt in range(MAX_REPORT_ATTEMPTS):
            user_prompt = self._build_final_prompt(
                prompt, 
                attempt, 
                last_error,
            )
            response = self.llm.chat_json_with_assistant(
                REPORT_FINAL_SYSTEM_PROMPT,
                current_report,
                user_prompt,
                REPORT_SCHEMA,
            )

            try:
                result = parse_report_result(response.content)
            except ValueError as exc:
                last_error = exc
                continue

            return GeneratedReport(
                report_markdown=result["report_markdown"],
                assessment=result["assessment"],
            )

        raise ValueError(f"Invalid structured report response: {last_error}")

    def _extract_markdown_update(self, content: str) -> str:
        try:
            data = json.loads(content)
        except (JSONDecodeError, TypeError):
            return content

        if not isinstance(data, dict):
            return content

        report_markdown = data.get("report_markdown")
        if isinstance(report_markdown, str) and report_markdown.strip():
            return report_markdown

        return content


    def _build_final_prompt(
        self,
        prompt: str,
        attempt: int,
        last_error: Exception | None,
    ) -> str:
        if attempt == 0 or last_error is None:
            return prompt

        return f"""
        {prompt}

        The previous response did not match the required schema:

        {last_error}

        Retry once and return only a valid JSON object matching the schema.
        """
