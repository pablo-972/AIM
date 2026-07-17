from collections import Counter
from typing import Any, Iterable

from core.utils.postprocessing.procmon.common import (
    MAX_REGISTRY_ITEMS,
    collection,
    counter_groups,
    generic_item_key,
)


def registry_result(state: dict[str, Any]) -> dict[str, Any]:
    registry = state["registry"]

    created_items = list(registry["created"].values())
    modified_items = list(registry["modified"].values())
    deleted_items = list(registry["deleted"].values())

    return {
        "created": collection(
            created_items,
            MAX_REGISTRY_ITEMS,
            _registry_groups(created_items, include_value_type=False),
            generic_item_key,
        ),
        "modified": collection(
            modified_items,
            MAX_REGISTRY_ITEMS,
            _registry_groups(modified_items, include_value_type=True),
            generic_item_key,
        ),
        "deleted": collection(
            deleted_items,
            MAX_REGISTRY_ITEMS,
            _registry_groups(deleted_items, include_value_type=False),
            generic_item_key,
        ),
    }


def registry_item(path: str, operation: str) -> dict[str, Any]:
    key_path, value_name = _registry_path_parts(path)
    return {
        "path": path,
        "key_path": key_path,
        "value_name": value_name,
        "operation": operation,
        "value_type": None,
        "data": None,
        "count": 0,
        "first_seen": "",
        "last_seen": "",
    }


def _registry_groups(
    items: Iterable[dict[str, Any]],
    include_value_type: bool,
) -> list[dict[str, Any]]:
    counters = {
        "hive": Counter(),
        "registry_root": Counter(),
        "operation": Counter(),
    }

    if include_value_type:
        counters["value_type"] = Counter()

    for item in items:
        key_path = item.get("key_path") or item.get("path", "")
        count = item.get("count", 1)

        hive = _registry_hive(key_path)
        registry_root = _registry_root(key_path)
        operation = item.get("operation", "")

        counters["hive"][hive] += count
        counters["registry_root"][registry_root] += count
        counters["operation"][operation] += count

        if include_value_type:
            value_type = item.get("value_type") or ""
            counters["value_type"][value_type] += count

    return counter_groups(counters)


def _registry_path_parts(path: str) -> tuple[str, str | None]:
    parts = path.rsplit("\\", 1)
    if len(parts) == 1:
        return path, None
    
    return parts[0], parts[1]


def _registry_hive(path: str) -> str:
    return path.split("\\", 1)[0]


def _registry_root(path: str) -> str:
    parts = path.split("\\")
    return "\\".join(parts[:4]) if len(parts) >= 4 else path
