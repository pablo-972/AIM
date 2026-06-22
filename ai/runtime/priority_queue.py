import heapq
import json
from itertools import count
from typing import Any


class TargetPriorityQueue:
    def __init__(self) -> None:
        self._queue: list[tuple[int, int, dict[str, Any]]] = []
        self._queued: set[str] = set()
        self._visited: set[str] = set()
        self._counter = count()


    def _key(self, target: dict[str, Any]) -> str:
        return json.dumps(
            {
                "tool": target["tool"],
                "parameters": target["parameters"],
            },
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )


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
