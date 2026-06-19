from collections.abc import Iterator
from typing import Any

from config import STATIC_AGENT_RESULT_FILENAME, STATIC_AGENT_TOOLS_PATH
from utils.io.files import load_json
from utils.logger import Logger
from ai.agents.static import StaticAgent
from ai.runtime.executor import AgentStepExecutor
from ai.runtime.memory import AgentMemory
from ai.runner.base import BaseAIRunner
from tools.runner.static import StaticAgentToolRunner


STRING_CHUNK_SIZE = 80


class StaticAgentRunner(BaseAIRunner):
    def __init__(
        self,
        context: Any,
        model_registry: Any,
        strings: list[str],
        agent_tools: StaticAgentToolRunner,
    ) -> None:
        super().__init__(context)

        self.model_registry = model_registry
        self.strings = strings
        self.agent_tools = agent_tools
        self.available_static_tools = load_json(self.context.output, STATIC_AGENT_TOOLS_PATH) or {}
        

    def _iter_string_chunks(self, chunk_size: int = STRING_CHUNK_SIZE) -> Iterator[list[str]]:
        for index in range(0, len(self.strings), chunk_size):
            yield self.strings[index:index + chunk_size]


    def _execute_tool_for_chunk(self, tool_name: str, parameters: dict[str, Any], chunk_index: int, strings_chunk: list[str]) -> dict[str, Any]:
        tool_context = {
            "chunk_index": chunk_index,
            "message_block": strings_chunk,
        }
        return self.agent_tools.execute(tool_name, parameters, tool_context)


    def _analyze_chunk(self, agent: StaticAgent, strings_chunk: list[str], chunk_index: int) -> dict[str, Any] | None:
        try:
            decision = agent.analyze_strings_chunk(strings_chunk, self.available_static_tools)
        except Exception as exc:
            Logger.error(f"Static agent failed on chunk {chunk_index}: {exc}")
            return None
        decision.setdefault("chunk_index", chunk_index)
        return decision


    def run(self) -> None:
        Logger.info("Running AI static agent")

        llm = self.model_registry.create_agent_client("static", profile_override=self.context.profile)
        agent = StaticAgent(llm)
        memory = AgentMemory(output_dir=self.context.output, filename=STATIC_AGENT_RESULT_FILENAME, flush_interval=1)
        step_executor = AgentStepExecutor(available_tools=self.available_static_tools)

        try:
            for chunk_index, strings_chunk in enumerate(self._iter_string_chunks(), start=1):
                decision = self._analyze_chunk(agent, strings_chunk, chunk_index)
                if decision is None:
                    continue

                tool_name, tool_output = step_executor.execute(
                    decision,
                    lambda name, params: self._execute_tool_for_chunk(
                        name,
                        params,
                        chunk_index,
                        strings_chunk,
                    ),
                )
                memory.record(decision, tool_name, tool_output)
        finally:
            memory.close()

        Logger.success("Static agent finished")
