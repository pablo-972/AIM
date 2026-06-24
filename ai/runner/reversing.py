from typing import Any

from config import REVERSING_AGENT_RESULT_FILENAME, REVERSING_AGENT_TOOLS_PATH
from utils.io.files import load_json
from utils.logger import Logger
from utils.postprocessing.reversing import ReversingPostprocessor
from orchestrator.context import AnalysisContext
from tools.runner.reversing import ReversingAgentToolRunner
from ai.agents.reversing import ReversingAgent
from ai.model_registry import ModelRegistry
from ai.runner.base import BaseAIRunner
from ai.runtime.memory import AgentMemory
from ai.runtime.reversing.evidence import ReversingEvidenceEvaluator
from ai.runtime.reversing.exploration import ReversingExplorationLoop
from ai.runtime.reversing.initialization import ReversingInvestigationInitializer
from ai.runtime.reversing.targets import ReversingTargetQueue





class ReversingAgentRunner(BaseAIRunner):
    def __init__(
        self,
        context: AnalysisContext,
        model_registry: ModelRegistry,
    ) -> None:
        super().__init__(context)
        self.model_registry = model_registry
        self.available_tools: dict[str, Any] = load_json(
            REVERSING_AGENT_TOOLS_PATH.parent,
            REVERSING_AGENT_TOOLS_PATH.name,
        ) or {}
        self.memory = AgentMemory(
            output_dir=self.context.output,
            filename=REVERSING_AGENT_RESULT_FILENAME,
            agent_name="reverse_agent",
        )
        self.targets = ReversingTargetQueue(
            available_tools=self.available_tools,
            memory=self.memory,
        )
        self.postprocessor = ReversingPostprocessor(self.available_tools)

    def run(self) -> None:
        Logger.info("Running AI reversing agent")

        try:
            agent = self._create_agent()
            initialization = ReversingInvestigationInitializer(
                context=self.context,
                targets=self.targets,
                available_tools=self.available_tools,
            ).initialize(agent)

            self.memory.record(
                decision=initialization.seed_decision(),
                input_ref={
                    "type": "initialization",
                    "value": initialization.input_source,
                },
                error=initialization.seed_error,
            )
            self.targets.enqueue(
                initialization.targets,
                source=initialization.source,
            )

            evaluator = ReversingEvidenceEvaluator(
                agent=agent,
                enrichment=initialization.enrichment,
                available_tools=self.available_tools,
                postprocessor=self.postprocessor,
                memory=self.memory,
                targets=self.targets,
            )
            ReversingExplorationLoop(
                max_targets=self.context.reversing_max_targets,
                targets=self.targets,
                tool_runner=ReversingAgentToolRunner(self.context),
                evaluator=evaluator,
                postprocessor=self.postprocessor,
                memory=self.memory,
            ).run()
        except KeyboardInterrupt:
            self.memory.close(status="interrupted")
            raise
        except Exception as exc:
            self.memory.fail(str(exc))
            raise
        else:
            self.memory.close()

        Logger.success("Reversing agent finished")

    def _create_agent(self) -> ReversingAgent:
        llm = self.model_registry.create_agent_client(
            "reversing",
            profile_override=self.context.profile,
        )
        return ReversingAgent(llm)
