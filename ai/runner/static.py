from collections.abc import Iterator
from typing import Any
from config import (
    STATIC_AGENT_RESULT_FILENAME,
    STATIC_AGENT_TOOLS_PATH,
    THREAT_ACTOR_MESSAGES_FILENAME,
)
from utils.io.files import load_json
from utils.logger import Logger
from ai.agents.static import StaticAgent
from ai.runtime.executor import AgentStepExecutor
from ai.runtime.memory import AgentMemory
from ai.runner.base import BaseAIRunner
from ai.model_registry import ModelRegistry
from orchestrator.context import AnalysisContext
from tools.runner.static import StaticAgentToolRunner

STRING_CHUNK_SIZE = 80


class StaticAgentRunner(BaseAIRunner):
    def __init__(
        self,
        context: AnalysisContext,
        model_registry: ModelRegistry,
        strings: list[str],
        agent_tools: StaticAgentToolRunner,
    ) -> None:
        super().__init__(context)

        self.model_registry: ModelRegistry = model_registry
        self.strings: list[str] = strings
        self.agent_tools: StaticAgentToolRunner = agent_tools
        self.available_static_tools: dict[str, Any] = (
            load_json(self.context.output, STATIC_AGENT_TOOLS_PATH) or {}
        )
        
    def run(self) -> None:
        Logger.info("Running AI static agent")

        llm = self.model_registry.create_agent_client(
            "static", 
            profile_override=self.context.profile
        )
        agent = StaticAgent(llm)
        memory = AgentMemory(
            output_dir=self.context.output,
            filename=STATIC_AGENT_RESULT_FILENAME,
            agent_name="static_agent",
        )
        step_executor = AgentStepExecutor(available_tools=self.available_static_tools)

        try:
            for chunk_index, strings_chunk in enumerate(self._iter_string_chunks(), start=1):
                input_ref = {
                    "type": "strings_chunk",
                    "index": chunk_index,
                    "value": None,
                }

                try:
                    decision = agent.analyze_strings_chunk(
                        strings_chunk,
                        self.available_static_tools,
                    )
                except Exception as exc:
                    error = f"Static agent failed on chunk {chunk_index}: {exc}"
                    Logger.error(error)
                    memory.record(
                        decision={
                            "thought": "The chunk could not be analyzed.",
                            "confidence": "low",
                            "action": "none",
                            "parameters": {},
                        },
                        input_ref=input_ref,
                        error=error,
                    )
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

                artifact_ref = self._artifact_ref(tool_output)
                finding = self._finding(decision, tool_output, artifact_ref)
                memory.record(
                    decision=decision,
                    tool_name=tool_name,
                    tool_output=tool_output,
                    input_ref=input_ref,
                    finding=finding,
                    artifact_ref=artifact_ref,
                )
        except Exception as exc:
            memory.fail(str(exc))
            raise
        else:
            memory.close()

        Logger.success("Static agent finished")
    
    def _iter_string_chunks(self, chunk_size: int = STRING_CHUNK_SIZE) -> Iterator[list[str]]:
        for index in range(0, len(self.strings), chunk_size):
            yield self.strings[index:index + chunk_size]

    def _execute_tool_for_chunk(
            self, 
            tool_name: str, 
            parameters: dict[str, Any], 
            chunk_index: int, 
            strings_chunk: list[str]
        ) -> dict[str, Any]:
        tool_context = {
            "chunk_index": chunk_index,
            "message_block": strings_chunk,
        }
        return self.agent_tools.execute(tool_name, parameters, tool_context)

    def _artifact_ref(
        self,
        tool_output: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(tool_output, dict):
            return None

        item_id = tool_output.get("item_id")
        if tool_output.get("success") is not True or item_id is None:
            return None

        return {
            "filename": THREAT_ACTOR_MESSAGES_FILENAME,
            "item_id": item_id,
        }

    def _finding(
        self,
        decision: dict[str, Any],
        tool_output: dict[str, Any] | None,
        artifact_ref: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if (
            not isinstance(tool_output, dict)
            or tool_output.get("saved") is not True
            or artifact_ref is None
        ):
            return None

        return {
            "type": "threat_actor_message",
            "confidence": decision.get("confidence", "low"),
            "summary": "Threat actor message block identified.",
            "artifact_ref": artifact_ref,
        }



