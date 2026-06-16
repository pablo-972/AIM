from utils.logger import Logger
from utils.io.files import load_json
from config import STATIC_AGENT_RESULT_FILENAME, STATIC_AGENT_TOOLS_PATH
from ai.runner.base import BaseAIRunner
from ai.agents.static import StaticAgent
from ai.runtime.memory import AgentMemory
from ai.runtime.executor import AgentStepExecutor


STRING_CHUNK_SIZE = 80


class StaticAgentRunner(BaseAIRunner):
    def __init__(self, context, model_registry, strings, tool_runner):
        super().__init__(context)

        self.strings = strings
        self.model_registry = model_registry
        self.tool_runner = tool_runner
        self.available_static_tools = load_json(self.context.output, STATIC_AGENT_TOOLS_PATH) or {}


    def _break_strings_into_chunks(self, strings: list[str], chunk_size: int):
        for i in range(0, len(strings), chunk_size):
            yield strings[i:i + chunk_size]


    def _execute_tool(self, tool_name: str, parameters: dict, chunk_index: int, strings_chunk: list[str]) -> dict:
        context = {"chunk_index": chunk_index, "message_block": strings_chunk}
        return self.tool_runner.execute_agent_tool(tool_name, parameters, context)


    def run(self):
        Logger.info("Running AI static agent")
        llm = self.model_registry.create_agent_client("static", profile_override=self.context.profile)
        static_agent = StaticAgent(llm)
        memory = AgentMemory(output_dir=self.context.output, filename=STATIC_AGENT_RESULT_FILENAME)
        step_executor = AgentStepExecutor(available_tools=self.available_static_tools)


        for chunk_index, strings_chunk in enumerate(self._break_strings_into_chunks(self.strings, STRING_CHUNK_SIZE), start=1):
            try:
                decision = static_agent.analyze_strings_chunk(strings_chunk, self.available_static_tools)
            except Exception as e:
                Logger.error(f"Static agent failed on chunk {chunk_index}: {e}")
                continue
            
            decision.setdefault("chunk_index", chunk_index)

            tool_name, tool_output = step_executor.execute(
                decision,
                lambda tool_name, parameters: self._execute_tool(tool_name, parameters, chunk_index, strings_chunk),
            )
            memory.record(decision, tool_name, tool_output)

        memory.flush()
        Logger.success("Finish static agent")
