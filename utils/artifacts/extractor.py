class JsonExtractor:
    def __init__(self, data: dict | None):
        self.data = data if isinstance(data, dict) else {}


    def get_static_tools(self) -> dict:
        phases = self.data.get("phases", {})
        static_phase = phases.get("static", {}) if isinstance(phases, dict) else {}
        tools = static_phase.get("tools", {}) if isinstance(static_phase, dict) else {}

        return tools if isinstance(tools, dict) else {}


    def get_tool_result(self, tool_name: str) -> dict:
        result = self.get_static_tools().get(tool_name, {})

        return result if isinstance(result, dict) else {}


    def get_tool_data(self, tool_name: str):
        tool = self.get_tool_result(tool_name)
        if tool.get("status") != "ok":
            return None
        
        return tool.get("data")


    def get_static_strings(self) -> list[str]:
        data = self.get_tool_data("strings") or {}
        strings = data.get("parsed_strings", []) if isinstance(data, dict) else []

        return strings if isinstance(strings, list) else []


    def get_threat_actor_message_blocks(self) -> list:
        items = self.data.get("items", [])
        if not isinstance(items, list):
            return []

        return [
            item.get("message_block")
            for item in items
            if isinstance(item, dict) and item.get("message_block")
        ]

