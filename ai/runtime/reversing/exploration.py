from typing import Any, Protocol

from utils.logger import Logger
from utils.postprocessing.reversing import ReversingPostprocessor
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
        depth: int,
        targets: "ReversingTargetQueue",
        tool_runner: ReversingToolExecutor,
        evaluator: EvidenceEvaluator,
        postprocessor: ReversingPostprocessor,
        memory: "AgentMemory",
    ) -> None:
        self.depth = depth
        self.targets = targets
        self.tool_runner = tool_runner
        self.evaluator = evaluator
        self.postprocessor = postprocessor
        self.memory = memory

    def run(self) -> None:
        while (
            self.targets.has_items()
            and self.targets.visited_count() < self.depth
        ):
            target = self.targets.pop()
            Logger.info(
                f"Reversing agent target: {target['tool']} "
                f"({self.targets.visited_count()}/{self.depth})"
            )
            tool_output = self.tool_runner.execute(
                target["tool"],
                target["parameters"],
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
