from typing import Any

DEFAULT_FINDINGS_BATCH_SIZE = 2
DEFAULT_DYNAMIC_EVIDENCE_LIMIT = 3


def get_static_strings_from_tool_results(results: dict[str, Any]) -> list[str]:
    tool_result = results.get("strings")
    if not isinstance(tool_result, dict):
        return []

    data = tool_result.get("data")
    if not isinstance(data, dict):
        return []

    strings = data.get("parsed_strings")
    if not isinstance(strings, list):
        return []

    return [
        string
        for string in strings
        if isinstance(string, str)
    ]


def batched_findings(
    findings: list[dict[str, Any]],
    batch_size: int = DEFAULT_FINDINGS_BATCH_SIZE,
) -> list[list[dict[str, Any]]]:
    batch_size = max(1, batch_size)

    return [
        findings[index:index + batch_size]
        for index in range(0, len(findings), batch_size)
    ]


class JsonExtractor:
    def __init__(self, data: dict[str, Any] | None) -> None:
        self.data = data if isinstance(data, dict) else {}

    def get_phase(self, phase_name: str) -> dict[str, Any]:
        phases = self._dict_or_empty(self.data.get("phases"))
        phase_name = phases.get(phase_name)

        return self._dict_or_empty(phase_name)

    def get_phase_tools(self, phase_name: str) -> dict[str, Any]:
        phase = self.get_phase(phase_name)
        tools = phase.get("tools")

        return self._dict_or_empty(tools)

    def get_phase_tool_result(
        self,
        phase_name: str,
        tool_name: str,
    ) -> dict[str, Any]:
        phase_tools = self.get_phase_tools(phase_name)
        phase_tools_result = phase_tools.get(tool_name)

        return self._dict_or_empty(phase_tools_result)

    def get_phase_tool_data(
        self,
        phase_name: str,
        tool_name: str,
    ) -> Any | None:
        tool = self.get_phase_tool_result(phase_name, tool_name)
        status = tool.get("status")

        if status != "ok":
            return None

        data = tool.get("data")
        return data

    def get_findings(self, finding_type: str | None = None) -> list[dict[str, Any]]:
        findings = self._list_of_dicts(self.data.get("findings"))
        if finding_type is None:
            return findings

        filtered_findings = []
        for finding in findings:
            type = finding.get("type")
            if type != finding_type:
                continue

            filtered_findings.append(finding)
        
        return filtered_findings

    def get_static_tools(self) -> dict[str, Any]:
        return self.get_phase_tools("static")

    def get_tool_result(self, tool_name: str) -> dict[str, Any]:
        return self.get_phase_tool_result("static", tool_name)

    def get_tool_data(self, tool_name: str) -> Any | None:
        return self.get_phase_tool_data("static", tool_name)

    def get_static_inference_findings(self) -> list[dict[str, Any]]:
        findings = []
        threat_actor_messages = self.get_findings("threat_actor_message")

        for finding in threat_actor_messages:
            text = finding.get("text")
            if not text:
                continue

            findings.append(finding)
        
        return findings

    def get_dynamic_inference_findings(
        self,
        evidence_limit: int = DEFAULT_DYNAMIC_EVIDENCE_LIMIT,
    ) -> list[dict[str, Any]]:
        findings = []
        dynamic_behavior = self.get_findings("dynamic_behavior")

        for finding in dynamic_behavior:
            is_dynamic_finding = self._is_dynamic_inference_finding(finding)
            if not is_dynamic_finding:
                continue

            dynamic_finding = self._dynamic_inference_finding(finding, evidence_limit)
            findings.append(dynamic_finding)

        return findings
    

    def _dict_or_empty(self, value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _list_of_dicts(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []

        items = []
        for item in value:
            if not isinstance(item, dict):
                continue
            
            items.append(item)

        return items

    def _is_dynamic_inference_finding(self, finding: dict[str, Any]) -> bool:
        explanation = finding.get("explanation")
        return isinstance(explanation, str) and bool(explanation.strip())

    def _dynamic_inference_finding(
        self,
        finding: dict[str, Any],
        evidence_limit: int,
    ) -> dict[str, Any]:
        evidence = finding.get("evidence")
        evidence_count = self._evidence_count(evidence)
        evidence = self._limited_evidence(
            evidence,
            evidence_limit,
        )

        confidence = finding.get("confidence")
        category = finding.get("category")
        tone = finding.get("tone")
        source = finding.get("source")
        explanation = finding.get("explanation")

        return {
            "confidence": confidence,
            "category": category,
            "tone": tone,
            "source": source,
            "explanation": explanation,
            "evidence": evidence,
            "evidence_count": evidence_count,
        }

    def _limited_evidence(
        self,
        evidence: Any,
        limit: int,
    ) -> Any:
        if not isinstance(evidence, list):
            return evidence

        limit = max(1, limit)

        return evidence[:limit]

    def _evidence_count(self, evidence: Any) -> int:
        if isinstance(evidence, list):
            return len(evidence)

        if evidence is None:
            return 0

        return 1
