import heapq
from itertools import count
from typing import Any

from core.ai.runtime.reversing.parameters import target_dedup_key


class TargetPriorityQueue:
    def __init__(self) -> None:
        self._queue: list[tuple[int, int, dict[str, Any]]] = []
        self._queued: set[str] = set()
        self._visited: set[str] = set()
        self._counter = count()

    def push(self, target: dict[str, Any]) -> bool:
        key = self._key(target)
        if key in self._queued or key in self._visited:
            return False

        heapq.heappush(
            self._queue,
            (-target["priority"], next(self._counter), target),
        )
        self._queued.add(key)
        return True

    def pop(self) -> dict[str, Any]:
        _, _, target = heapq.heappop(self._queue)
        key = self._key(target)
        self._queued.discard(key)
        self._visited.add(key)
        return target

    def visited_count(self) -> int:
        return len(self._visited)

    def size(self) -> int:
        return len(self._queue)

    def has_items(self) -> bool:
        return bool(self._queue)

    def _key(self, target: dict[str, Any]) -> str:
        tool = target.get("tool")
        parameters = target.get("parameters")
        return target_dedup_key(tool, parameters)
