from typing import Any


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


class JsonExtractor:
    def __init__(self, data: dict[str, Any] | None) -> None:
        self.data: dict[str, Any] = data if isinstance(data, dict) else {}

    def get_static_tools(self) -> dict[str, Any]:
        phases = self.data.get("phases", {})
        static_phase = phases.get("static", {}) if isinstance(phases, dict) else {}
        tools = static_phase.get("tools", {}) if isinstance(static_phase, dict) else {}

        return tools if isinstance(tools, dict) else {}

    def get_tool_result(self, tool_name: str) -> dict[str, Any]:
        result = self.get_static_tools().get(tool_name, {})

        return result if isinstance(result, dict) else {}

    def get_tool_data(self, tool_name: str) -> Any | None:
        tool = self.get_tool_result(tool_name)
        if tool.get("status") != "ok":
            return None
        
        return tool.get("data")

    def get_static_strings(self) -> list[str]:
        data = self.get_tool_data("strings") or {}
        strings = data.get("parsed_strings", []) if isinstance(data, dict) else []

        return strings if isinstance(strings, list) else []

    def get_static_inference_findings(self) -> list[dict[str, Any]]:
        findings = self.data.get("findings", [])
        if not isinstance(findings, list):
            return []

        return [
            finding
            for finding in findings
            if isinstance(finding, dict)
            and finding.get("type") == "threat_actor_message"
            and isinstance(finding.get("text"), str)
            and finding.get("text")
        ]
