from typing import Any

DEFAULT_FINDINGS_BATCH_SIZE = 2


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
        return self._dict_or_empty(phases.get(phase_name))

    def get_phase_tools(self, phase_name: str) -> dict[str, Any]:
        return self._dict_or_empty(self.get_phase(phase_name).get("tools"))

    def get_phase_tool_result(
        self,
        phase_name: str,
        tool_name: str,
    ) -> dict[str, Any]:
        phase_tool_result = self.get_phase_tools(phase_name).get(tool_name)
        return self._dict_or_empty(phase_tool_result)

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
        findings = self._list_of_dicts(self.data.get("findings"))
        if finding_type is None:
            return findings

        return [
            finding
            for finding in findings
            if finding.get("type") == finding_type
        ]

    def get_static_tools(self) -> dict[str, Any]:
        return self.get_phase_tools("static")

    def get_tool_result(self, tool_name: str) -> dict[str, Any]:
        return self.get_phase_tool_result("static", tool_name)

    def get_tool_data(self, tool_name: str) -> Any | None:
        return self.get_phase_tool_data("static", tool_name)

    def get_static_inference_findings(self) -> list[dict[str, Any]]:
        return [
            finding
            for finding in self.get_findings("threat_actor_message")
            if self._list_of_strings(finding.get("text"))
        ]
    

    def _dict_or_empty(self, value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _list_of_dicts(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []

        return [
            item
            for item in value
            if isinstance(item, dict)
        ]

    def _list_of_strings(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []

        return [
            item
            for item in value
            if isinstance(item, str)
        ]