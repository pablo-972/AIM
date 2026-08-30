from typing import Any

from core.ai.runtime.reversing.priority_queue import TargetPriorityQueue
from core.ai.runtime.reversing.target_validation import (
    ReversingTargetValidator,
    TargetValidationStatus,
)
from core.ai.runtime.tool_validator import validate_tool_parameters
from core.ai.runtime.reversing.memory import ReversingAgentMemory

DEFAULT_TARGET_PRIORITY = 50


class ReversingTargetQueue:
    def __init__(
        self,
        available_tools: dict[str, Any],
        memory: ReversingAgentMemory,
        validator: ReversingTargetValidator | None = None,
    ) -> None:
        self.available_tools = available_tools
        self.memory = memory
        self.target_validator = validator or ReversingTargetValidator()
        self.priority_queue = TargetPriorityQueue()

    def enqueue(self, targets: Any, source: str) -> int:
        return len(self.enqueue_targets(targets, source))

    def enqueue_targets(self, targets: Any, source: str) -> list[dict[str, Any]]:
        if not isinstance(targets, list):
            return []

        added = []
        for target in targets:
            prepared_target = self._prepare_target(target, source)
            if (
                prepared_target is not None
                and self.priority_queue.push(prepared_target)
            ):
                added.append(prepared_target)
                self.memory.record_queue_event(
                    action="added",
                    target=prepared_target,
                    queue_size=self.priority_queue.size(),
                    source=source,
                )

        return added

    def enqueue_resume(self, target: dict[str, Any], source: str) -> bool:
        if target.get("_resume") is not True:
            return False

        if not self.priority_queue.push(target):
            return False

        self.memory.record_queue_event(
            action="added",
            target=target,
            queue_size=self.priority_queue.size(),
            source=source,
        )
        return True

    def pop(self) -> dict[str, Any]:
        target = self.priority_queue.pop()
        self.memory.record_queue_event(
            action="removed",
            target=target,
            queue_size=self.priority_queue.size(),
            source="execution",
        )

        return target

    def pop_resume(self) -> dict[str, Any] | None:
        target = self.priority_queue.pop_resume()
        if target is None:
            return None

        self.memory.record_queue_event(
            action="removed",
            target=target,
            queue_size=self.priority_queue.size(),
            source="pending_chunk",
        )
        return target

    def has_items(self) -> bool:
        return self.priority_queue.has_items()

    def next_is_resume(self) -> bool:
        return self.priority_queue.next_is_resume()

    def has_resume(self) -> bool:
        return self.priority_queue.has_resume()

    def visited_count(self) -> int:
        return self.priority_queue.visited_count()

    def prepare_targets(
        self,
        targets: Any,
        source: str | None = None,
    ) -> list[dict[str, Any]]:
        if not isinstance(targets, list):
            return []

        prepared_targets = []
        for target in targets:
            prepared_target = self._prepare_target(target, source=source)

            if prepared_target is not None:
                prepared_targets.append(prepared_target)

        return prepared_targets

    def _prepare_target(self, target: Any, source: str | None) -> dict[str, Any] | None:
        if not isinstance(target, dict):
            return None

        tool_name = target.get("tool")
        parameters = target.get("parameters")

        if not isinstance(tool_name, str) or not isinstance(parameters, dict):
            return None

        validation = self.target_validator.validate(
            tool_name,
            parameters,
            self.available_tools,
        )
        if validation.status == TargetValidationStatus.REJECTED:
            self._record_rejected(validation.to_dict(), source)
            return None

        if validation.tool is None:
            self._record_rejected(validation.to_dict(), source)
            return None

        tool_name = validation.tool
        parameters = validation.parameters
        tool_spec = self.available_tools.get(tool_name)

        if not isinstance(tool_spec, dict):
            self._record_rejected(validation.to_dict(), source)
            return None
        if not validate_tool_parameters(parameters, tool_spec):
            self._record_rejected(validation.to_dict(), source)
            return None

        try:
            priority = int(target.get("priority", DEFAULT_TARGET_PRIORITY))
        except (TypeError, ValueError):
            priority = DEFAULT_TARGET_PRIORITY

        priority = max(1, min(priority, 100))

        prepared_target = {
            "tool": tool_name,
            "parameters": parameters,
            "priority": priority,
            "validation": validation.to_dict(),
        }
        if validation.canonical_target is not None:
            prepared_target["canonical_target"] = validation.canonical_target
        prepared_target.update(self._trace_metadata(target))

        return prepared_target

    def _trace_metadata(self, target: dict[str, Any]) -> dict[str, Any]:
        metadata = {}
        for key in (
            "origin_tool",
            "origin_target",
            "discovered_target",
            "relation",
        ):
            value = target.get(key)
            if isinstance(value, str) and value:
                metadata[key] = value

        return metadata

    def _record_rejected(
        self,
        validation: dict[str, Any],
        source: str | None,
    ) -> None:
        if source is None:
            return

        self.memory.record_queue_event(
            action="rejected",
            target={
                "validation": validation,
            },
            queue_size=self.priority_queue.size(),
            source=source,
        )
