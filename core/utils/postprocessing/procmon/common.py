import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable


MAX_PROCESS_ITEMS = 100
MAX_IMAGE_ITEMS = 250
MAX_FILE_ITEMS = 100
MAX_RENAME_ITEMS = 100
MAX_REGISTRY_ITEMS = 150
MAX_NETWORK_ITEMS = 150
MAX_GROUPS = 50


def collection(
    items: list[Any],
    limit: int,
    groups: list[dict[str, Any]],
    sort_key: Callable[[Any], Any],
    selector: Callable[[list[Any], int], list[Any]] | None = None,
) -> dict[str, Any]:
    total = len(items)
    sorted_items = sorted(items, key=sort_key)

    if selector is not None:
        visible = selector(sorted_items, limit)
    else:
        visible = sorted_items[:limit]

    return {
        "total": total,
        "truncated": total > len(visible),
        "groups": groups[:MAX_GROUPS],
        "items": visible,
    }


def merge_item(
    target: dict[tuple[Any, ...], dict[str, Any]],
    key: tuple[Any, ...],
    item: dict[str, Any],
    event: dict[str, str],
) -> dict[str, Any]:
    existing = target.get(key)
    if existing is None:
        existing = item
        target[key] = existing

    existing["count"] = int(existing.get("count", 0)) + 1
    update_seen(existing, event)

    return existing


def update_seen(item: dict[str, Any], event: dict[str, str]) -> None:
    seen = event.get("time_of_day", "")
    if not seen:
        return

    if not item.get("first_seen"):
        item["first_seen"] = seen

    item["last_seen"] = seen


def normalize_path(path: str) -> str:
    return str(path or "").strip().replace("/", "\\").lower()


def normalize_row_key(value: Any) -> str:
    return str(value or "").lower()


def generic_item_key(item: dict[str, Any]) -> str:
    keys = (
        "path",
        "from",
        "to",
        "process",
        "process_name",
        "operation",
    )

    values = [
        normalize_row_key(item.get(key))
        for key in keys
    ]

    return "|".join(values)


def extension(path: str) -> str:
    return Path(path).suffix.lower()


def directory(path: str) -> str:
    return str(Path(path).parent)


def directory_root(path: str) -> str:
    normalized = path.strip().replace("/", "\\")
    if not normalized:
        return ""

    parts = []
    for part in normalized.split("\\"):
        if part:
            parts.append(part)

    if not parts:
        return ""

    if normalized.startswith("\\\\"):
        if len(parts) >= 2:
            return f"\\\\{parts[0]}\\{parts[1]}"
        
        return normalized

    drive = parts[0]
    if drive.endswith(":"):
        if len(parts) == 1:
            return f"{drive}\\"
        
        if len(parts) == 2 and Path(parts[1]).suffix:
            return f"{drive}\\"
        
        return f"{drive}\\{parts[1]}"

    return parts[0]


def counter_groups(counters: dict[str, Counter]) -> list[dict[str, Any]]:
    groups = []
    for group_type, counter in counters.items():
        for value, count in sorted_counter(counter):
            if value in ("", None):
                continue

            groups.append({"type": group_type, "value": value, "count": count})

    return groups[:MAX_GROUPS]


def sorted_counter(counter: Counter) -> list[tuple[Any, int]]:
    return sorted(
        counter.items(), 
        key=lambda item: (-item[1], str(item[0])),
    )


def detail_value(detail: str, key: str) -> str:
    pattern = re.compile(r"(?:^|,\s*){0}:\s*([^,]+)".format(re.escape(key)), re.IGNORECASE)
    match = pattern.search(detail)

    return match.group(1).strip() if match else ""


def detail_number(detail: str, key: str) -> int | None:
    value = detail_value(detail, key)
    if not value:
        return None
    
    digits = re.sub(r"\D", "", value)
    return int(digits) if digits else None
