from typing import Any

from config import REVERSING_AGENT_RESULT_FILENAME, REVERSING_AGENT_TOOLS_PATH
from core.utils.io.files import load_json
from core.utils.logger import Logger
from core.utils.postprocessing.reversing import ReversingPostprocessor
from core.orchestrator.context import AnalysisContext
from core.tools.runner.reversing import ReversingAgentToolRunner
from core.ai.agents.reversing import ReversingAgent
from core.ai.model_registry import ModelRegistry
from core.ai.runner.base import BaseAIRunner
from core.ai.runtime.executor import AgentStepExecutor
from core.ai.runtime.memory import TraceMemory
from core.ai.runtime.reversing.evidence import ReversingEvidenceEvaluator
from core.ai.runtime.reversing.exploration import ReversingExplorationLoop
from core.ai.runtime.reversing.initialization import ReversingInvestigationInitializer
from core.ai.runtime.reversing.targets import ReversingTargetQueue


class ReversingAgentRunner(BaseAIRunner):
    def __init__(self, context: AnalysisContext, model_registry: ModelRegistry) -> None:
        super().__init__(context)
        self.model_registry = model_registry
        self.available_tools: dict[str, Any] = load_json(
            REVERSING_AGENT_TOOLS_PATH.parent,
            REVERSING_AGENT_TOOLS_PATH.name,
        ) or {}
        self.memory = TraceMemory(
            output_dir=self.context.output,
            filename=REVERSING_AGENT_RESULT_FILENAME,
            agent_name="reversing_agent",
        )
        self.targets = ReversingTargetQueue(
            available_tools=self.available_tools,
            memory=self.memory,
        )
        self.postprocessor = ReversingPostprocessor(self.available_tools)

    def run(self) -> None:
        agent = self._create_agent()

        try:
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
                tool_runner=ReversingAgentToolRunner(self.context.sample),
                step_executor=AgentStepExecutor(self.available_tools),
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

        

    def _create_agent(self) -> ReversingAgent:
        llm = self.model_registry.create_agent_client(
            "reversing",
            profile_override=self.context.profile,
        )
        return ReversingAgent(llm)
