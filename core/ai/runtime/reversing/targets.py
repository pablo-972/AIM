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
        if not isinstance(targets, list):
            return 0

        added = 0
        for target in targets:
            prepared_target = self._prepare_target(target, source)
            if (
                prepared_target is not None
                and self.priority_queue.push(prepared_target)
            ):
                added += 1
                self.memory.record_queue_event(
                    action="added",
                    target=prepared_target,
                    queue_size=self.priority_queue.size(),
                    source=source,
                )

        return added

    def pop(self) -> dict[str, Any]:
        target = self.priority_queue.pop()
        self.memory.record_queue_event(
            action="removed",
            target=target,
            queue_size=self.priority_queue.size(),
            source="execution",
        )

        return target

    def has_items(self) -> bool:
        return self.priority_queue.has_items()

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

    def rejection_context(self, target: Any) -> dict[str, Any] | None:
        if not isinstance(target, dict):
            return {
                "message": "Target is not a valid object.",
            }

        tool_name = target.get("tool")
        parameters = target.get("parameters")

        if not isinstance(tool_name, str) or not isinstance(parameters, dict):
            return {
                "message": "Target does not contain a valid tool and parameters.",
            }

        validation = self.target_validator.validate(
            tool_name,
            parameters,
            self.available_tools,
        )

        if validation.status == TargetValidationStatus.REJECTED:
            return validation.to_dict()

        if validation.tool is None:
            return validation.to_dict()

        tool_spec = self.available_tools.get(validation.tool)
        if not isinstance(tool_spec, dict):
            context = validation.to_dict()
            context["message"] = "Validated tool is not available."
            return context

        if not validate_tool_parameters(validation.parameters, tool_spec):
            context = validation.to_dict()
            context["message"] = "Validated tool parameters do not match the schema."
            return context

        return None

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
