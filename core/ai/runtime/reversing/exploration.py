from typing import Any, Protocol

from core.utils.logger import Logger
from core.utils.postprocessing.reversing import ReversingPostprocessor
from core.ai.runtime.executor import AgentStepExecutor
from core.utils.address import parse_address


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
        targets: Any,
        tool_runner: ReversingToolExecutor,
        step_executor: AgentStepExecutor,
        evaluator: EvidenceEvaluator,
        postprocessor: ReversingPostprocessor,
        memory: Any,
    ) -> None:
        self.max_targets = max_targets
        self.targets = targets
        self.tool_runner = tool_runner
        self.step_executor = step_executor
        self.evaluator = evaluator
        self.postprocessor = postprocessor
        self.memory = memory
        self.analyzed_functions: set[str] = set()

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
                if self._already_analyzed_function(target, tool_output):
                    continue

                self.evaluator.evaluate(target, tool_output)
            else:
                self._record_failure(target, tool_output)

    def _already_analyzed_function(
        self,
        target: dict[str, Any],
        tool_output: dict[str, Any],
    ) -> bool:
        if target.get("tool") != "disassembly":
            return False

        function_key = self._resolved_function_key(tool_output)
        if function_key is None:
            return False

        if function_key not in self.analyzed_functions:
            self.analyzed_functions.add(function_key)
            return False

        requested_address = target.get("parameters", {}).get("address")
        Logger.info(
            "Skipping disassembly analysis for "
            f"{requested_address}: function {function_key} was already analyzed"
        )
        return True

    def _resolved_function_key(self, tool_output: dict[str, Any]) -> str | None:
        data = tool_output.get("data")
        if not isinstance(data, dict):
            return None

        function = data.get("resolved_function") or data.get("function")
        address = parse_address(function)
        if address is None:
            return None

        return hex(address)

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
