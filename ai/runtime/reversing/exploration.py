from typing import TYPE_CHECKING, Any, Protocol

from utils.logger import Logger
from utils.postprocessing.reversing import ReversingPostprocessor
from ai.runtime.executor import AgentStepExecutor

if TYPE_CHECKING:
    from ai.runtime.memory import AgentMemory
    from ai.runtime.reversing.targets import ReversingTargetQueue


class ReversingToolExecutor(Protocol):
    def execute(
        self,
        tool_name: str,
        parameters: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ...


class EvidenceEvaluator(Protocol):
    def evaluate(
        self,
        target: dict[str, Any],
        tool_output: dict[str, Any],
    ) -> None:
        ...


class ReversingExplorationLoop:
    def __init__(
        self,
        max_targets: int,
        targets: "ReversingTargetQueue",
        tool_runner: ReversingToolExecutor,
        step_executor: AgentStepExecutor,
        evaluator: EvidenceEvaluator,
        postprocessor: ReversingPostprocessor,
        memory: "AgentMemory",
    ) -> None:
        self.max_targets = max_targets
        self.targets = targets
        self.tool_runner = tool_runner
        self.step_executor = step_executor
        self.evaluator = evaluator
        self.postprocessor = postprocessor
        self.memory = memory

    def run(self) -> None:
        while (
            self.targets.has_items()
            and self.targets.visited_count() < self.max_targets
        ):
            target = self.targets.pop()
            Logger.info(
                f"Reversing agent target: {target['tool']} "
                f"({self.targets.visited_count()}/{self.max_targets})"
            )
            tool_output = self.step_executor.execute_tool(
                target["tool"],
                target["parameters"],
                self.tool_runner.execute,
            )

            if tool_output.get("success") is True:
                self.evaluator.evaluate(target, tool_output)
            else:
                self._record_failure(target, tool_output)

    def _record_failure(
        self,
        target: dict[str, Any],
        tool_output: dict[str, Any],
    ) -> None:
        self.memory.record(
            decision={
                "thought": target["reason"],
                "confidence": "low",
                "action": target["tool"],
                "parameters": target["parameters"],
            },
            tool_name=target["tool"],
            tool_output=tool_output,
            input_ref=self.postprocessor.input_ref(target),
        )
