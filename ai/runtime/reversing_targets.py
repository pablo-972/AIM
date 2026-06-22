from typing import TYPE_CHECKING, Any

from ai.runtime.priority_queue import TargetPriorityQueue
from ai.runtime.validators import validate_tool_parameters

if TYPE_CHECKING:
    from ai.runtime.memory import AgentMemory


DEFAULT_TARGET_PRIORITY = 50
MAX_TARGET_REASON_LENGTH = 500


class ReversingTargetQueue:
    def __init__(
        self,
        available_tools: dict[str, Any],
        memory: "AgentMemory",
    ) -> None:
        self.available_tools = available_tools
        self.memory = memory
        self.queue = TargetPriorityQueue()


    def enqueue(self, targets: Any, source: str) -> None:
        if not isinstance(targets, list):
            return

        for target in targets:
            normalized = self._normalize(target)
            if normalized is not None and self.queue.push(normalized):
                self.memory.record_queue_event(
                    action="added",
                    target=normalized,
                    queue_size=self.queue.size(),
                    source=source,
                )


    def pop(self) -> dict[str, Any]:
        target = self.queue.pop()
        self.memory.record_queue_event(
            action="removed",
            target=target,
            queue_size=self.queue.size(),
            source="execution",
        )
        return target


    def has_items(self) -> bool:
        return self.queue.has_items()


    def visited_count(self) -> int:
        return self.queue.visited_count()


    def fallback_targets(
        self,
        reconnaissance: dict[str, Any],
    ) -> list[dict[str, Any]]:
        targets = [
            {
                "tool": "import_xrefs",
                "parameters": {"import_name": item["name"]},
                "priority": 90,
                "reason": "Suspicious import discovered during reconnaissance.",
            }
            for item in reconnaissance["suspicious_imports"][:5]
            if item.get("name")
        ]
        targets.extend(
            {
                "tool": "disassembly",
                "parameters": {
                    "function": item["name"],
                    "max_instructions": 200,
                },
                "priority": 80,
                "reason": "Large function discovered during reconnaissance.",
            }
            for item in reconnaissance["large_functions"][:3]
            if item.get("name")
        )
        targets.extend(
            {
                "tool": "string_xrefs",
                "parameters": {"value": item["value"]},
                "priority": 70,
                "reason": "Interesting string discovered during reconnaissance.",
            }
            for item in reconnaissance["interesting_strings"][:3]
            if item.get("value")
        )
        return targets[:6]


    def _normalize(self, target: Any) -> dict[str, Any] | None:
        if not isinstance(target, dict):
            return None

        tool_name = target.get("tool")
        parameters = target.get("parameters")
        if not isinstance(tool_name, str) or not isinstance(parameters, dict):
            return None

        tool_spec = self.available_tools.get(tool_name)
        if not isinstance(tool_spec, dict):
            return None
        if not validate_tool_parameters(parameters, tool_spec):
            return None

        try:
            priority = int(target.get("priority", DEFAULT_TARGET_PRIORITY))
        except (TypeError, ValueError):
            priority = DEFAULT_TARGET_PRIORITY

        return {
            "tool": tool_name,
            "parameters": parameters,
            "priority": max(1, min(priority, 100)),
            "reason": str(target.get("reason") or "").strip()[
                :MAX_TARGET_REASON_LENGTH
            ],
        }
