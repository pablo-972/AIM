from typing import Any


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

    def get_threat_actor_message_blocks(self) -> list[str | list[str]]:
        items = self.data.get("items", [])
        if not isinstance(items, list):
            return []

        blocks: list[str | list[str]] = []
        for item in items:
            if not isinstance(item, dict):
                continue

            block = item.get("message_block")
            if isinstance(block, str) and block:
                blocks.append(block)
            elif (
                isinstance(block, list)
                and block
                and all(isinstance(line, str) for line in block)
            ):
                blocks.append(block)

        return blocks

