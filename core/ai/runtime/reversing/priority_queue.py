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
        if target.get("_resume") is not True:
            self._visited.add(key)
        return target

    def pop_resume(self) -> dict[str, Any] | None:
        for index, (_, _, target) in enumerate(self._queue):
            if target.get("_resume") is True:
                _, _, resume_target = self._queue.pop(index)
                heapq.heapify(self._queue)
                self._queued.discard(self._key(resume_target))
                return resume_target

        return None

    def visited_count(self) -> int:
        return len(self._visited)

    def size(self) -> int:
        return len(self._queue)

    def has_items(self) -> bool:
        return bool(self._queue)

    def next_is_resume(self) -> bool:
        if not self._queue:
            return False

        _, _, target = self._queue[0]
        return target.get("_resume") is True

    def has_resume(self) -> bool:
        return any(
            target.get("_resume") is True
            for _, _, target in self._queue
        )

    def _key(self, target: dict[str, Any]) -> str:
        queue_key = target.get("_queue_key")
        if isinstance(queue_key, str) and queue_key:
            return queue_key

        tool = target.get("tool")
        canonical_target = target.get("canonical_target")
        if isinstance(tool, str) and isinstance(canonical_target, str):
            return f"{tool}:{canonical_target}"

        parameters = target.get("parameters")
        return target_dedup_key(tool, parameters)
