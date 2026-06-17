

class JsonExtractor:
    def __init__(self, data: dict | None):
        self.data = data or {}


    def get_static_tools(self) -> dict:
        return self.data.get("phases", {}).get("static", {}).get("tools", {})


    def get_tool_result(self, tool_name: str) -> dict:
        return self.get_static_tools().get(tool_name, {})


    def get_tool_data(self, tool_name: str):
        tool = self.get_tool_result(tool_name)
        if tool.get("status") != "ok":
            return None
        return tool.get("data")


    def get_static_strings(self) -> list[str]:
        data = self.get_tool_data("strings") or {}
        return data.get("parsed_strings", [])


    def get_threat_actor_message_blocks(self) -> list:
        return [
            item.get("message_block")
            for item in self.data.get("items", [])
            if item.get("message_block")
        ]

