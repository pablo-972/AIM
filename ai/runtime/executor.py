from ai.runtime.validators import NO_TOOL_ACTIONS, validate_agent_step


class AgentStepExecutor:
    def __init__(self, available_tools: dict):
        self.available_tools = available_tools


    def execute(self, decision: dict, tool_executor) -> tuple[str | None, dict | None]:
        if not validate_agent_step(decision, self.available_tools):
            return None, {"error": "Invalid agent step"}

        tool_name = decision.get("action")
        if tool_name in NO_TOOL_ACTIONS:
            return tool_name, None
        
        parameters = decision.get("parameters", {})
        return tool_name, tool_executor(tool_name, parameters)
    
    