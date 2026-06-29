from typing import Any

DEFAULT_FINDINGS_BATCH_SIZE = 2


def get_static_strings_from_tool_results(results: dict[str, Any]) -> list[str]:
    strings_result = results.get("strings")
    if not isinstance(strings_result, dict):
        return []

    strings_data = strings_result.get("data")
    if not isinstance(strings_data, dict):
        return []

    strings = strings_data.get("parsed_strings")
    if isinstance(strings, list) and all(
        isinstance(item, str) for item in strings
    ):
        return strings

    return []


def batched_findings(
    findings: list[dict[str, Any]],
    batch_size: int = DEFAULT_FINDINGS_BATCH_SIZE,
) -> list[list[dict[str, Any]]]:
    if batch_size < 1:
        batch_size = DEFAULT_FINDINGS_BATCH_SIZE

    return [
        findings[index:index + batch_size]
        for index in range(0, len(findings), batch_size)
    ]


class JsonExtractor:
    def __init__(self, data: dict[str, Any] | None) -> None:
        self.data: dict[str, Any] = data if isinstance(data, dict) else {}

    def get_phase(self, phase_name: str) -> dict[str, Any]:
        phases = self.data.get("phases", {})
        if not isinstance(phases, dict):
            return {}

        phase = phases.get(phase_name, {})
        return phase if isinstance(phase, dict) else {}

    def get_phase_tools(self, phase_name: str) -> dict[str, Any]:
        phase = self.get_phase(phase_name)
        tools = phase.get("tools", {})

        return tools if isinstance(tools, dict) else {}

    def get_phase_tool_result(
        self,
        phase_name: str,
        tool_name: str,
    ) -> dict[str, Any]:
        result = self.get_phase_tools(phase_name).get(tool_name, {})

        return result if isinstance(result, dict) else {}

    def get_phase_tool_data(
        self,
        phase_name: str,
        tool_name: str,
    ) -> Any | None:
        tool = self.get_phase_tool_result(phase_name, tool_name)
        if tool.get("status") != "ok":
            return None

        return tool.get("data")

    def get_findings(self, finding_type: str | None = None) -> list[dict[str, Any]]:
        findings = self.data.get("findings", [])
        if not isinstance(findings, list):
            return []

        normalized = [
            finding
            for finding in findings
            if isinstance(finding, dict)
        ]
        if finding_type is None:
            return normalized

        return [
            finding
            for finding in normalized
            if finding.get("type") == finding_type
        ]

    def get_static_tools(self) -> dict[str, Any]:
        return self.get_phase_tools("static")

    def get_tool_result(self, tool_name: str) -> dict[str, Any]:
        return self.get_phase_tool_result("static", tool_name)

    def get_tool_data(self, tool_name: str) -> Any | None:
        return self.get_phase_tool_data("static", tool_name)

    def get_static_strings(self) -> list[str]:
        data = self.get_tool_data("strings") or {}
        strings = data.get("parsed_strings", []) if isinstance(data, dict) else []

        return strings if isinstance(strings, list) else []

    def get_static_inference_findings(self) -> list[dict[str, Any]]:
        return [
            finding
            for finding in self.get_findings("threat_actor_message")
            if isinstance(finding.get("text"), str)
            and finding.get("text")
        ]
