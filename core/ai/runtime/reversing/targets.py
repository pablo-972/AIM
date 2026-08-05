from typing import Any

from core.ai.runtime.reversing.priority_queue import TargetPriorityQueue
from core.ai.runtime.validators import normalize_tool_parameters, validate_tool_parameters
from core.ai.runtime.memory import TraceMemory

DEFAULT_TARGET_PRIORITY = 50
MAX_TARGET_REASON_LENGTH = 500


class ReversingTargetQueue:
    def __init__(
        self,
        available_tools: dict[str, Any],
        memory: "TraceMemory",
    ) -> None:
        self.available_tools = available_tools
        self.memory = memory
        self.queue = TargetPriorityQueue()

    def enqueue(self, targets: Any, source: str) -> int:
        if not isinstance(targets, list):
            return 0

        added = 0
        for target in targets:
            normalized = self._normalize(target)
            if normalized is not None and self.queue.push(normalized):
                added += 1
                self.memory.record_queue_event(
                    action="added",
                    target=normalized,
                    queue_size=self.queue.size(),
                    source=source,
                )

        return added

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
        suspicious_imports = self._get_reconnaissance_items(
            reconnaissance,
            "suspicious_imports",
        )
        large_functions = self._get_reconnaissance_items(
            reconnaissance,
            "large_functions",
        )
        interesting_strings = self._get_reconnaissance_items(
            reconnaissance,
            "interesting_strings",
        )

        targets = []

        for item in suspicious_imports[:5]:
            import_name = item.get("name")

            if not import_name:
                continue

            target = {
                "tool": "import_xrefs",
                "parameters": {
                    "import_name": import_name,
                },
                "priority": 90,
                "reason": "Suspicious import discovered during reconnaissance.",
            }

            targets.append(target)

        for item in large_functions[:3]:
            address = item.get("address")

            if not isinstance(address, int):
                continue

            target = {
                "tool": "disassembly",
                "parameters": {
                    "address": hex(address),
                },
                "priority": 80,
                "reason": "Large function discovered during reconnaissance.",
            }

            targets.append(target)

        for item in interesting_strings[:3]:
            string_value = item.get("value")

            if not string_value:
                continue

            target = {
                "tool": "string_xrefs",
                "parameters": {
                    "value": string_value,
                },
                "priority": 70,
                "reason": "Interesting string discovered during reconnaissance.",
            }

            targets.append(target)

        return targets[:6]

    def valid_targets(self, targets: Any) -> list[dict[str, Any]]:
        if not isinstance(targets, list):
            return []

        normalized_targets = []
        for target in targets:
            normalized = self._normalize(target)

            if normalized is not None:
                normalized_targets.append(normalized)

        return normalized_targets

    def _get_reconnaissance_items(
        self,
        reconnaissance: dict[str, Any],
        key: str,
    ) -> list[dict[str, Any]]:
        items = reconnaissance.get(key, [])
        if not isinstance(items, list):
            return []

        return [
            item
            for item in items
            if isinstance(item, dict)
        ]

    def _normalize(self, target: Any) -> dict[str, Any] | None:
        if not isinstance(target, dict):
            return None

        tool_name = target.get("tool")
        parameters = target.get("parameters")

        if not isinstance(tool_name, str) or not isinstance(parameters, dict):
            return None

        parameters = normalize_tool_parameters(tool_name, parameters)
        tool_spec = self.available_tools.get(tool_name)

        if not isinstance(tool_spec, dict):
            return None
        if not validate_tool_parameters(parameters, tool_spec):
            return None

        try:
            priority = int(target.get("priority", DEFAULT_TARGET_PRIORITY))
        except (TypeError, ValueError):
            priority = DEFAULT_TARGET_PRIORITY

        reason = str(target.get("reason") or "").strip()[:MAX_TARGET_REASON_LENGTH]
        normalized_priority = max(1, min(priority, 100))

        return {
            "tool": tool_name,
            "parameters": parameters,
            "priority": normalized_priority,
            "reason": reason,
        }
