from collections import Counter
from pathlib import PureWindowsPath
from typing import Any, Iterable

from core.utils.postprocessing.procmon.common import (
    MAX_FILE_ITEMS,
    MAX_GROUPS,
    MAX_RENAME_ITEMS,
    collection,
    directory_root,
    extension,
    generic_item_key,
    normalize_path,
    sorted_counter,
)


FILESYSTEM_VISIBLE_ACTIONS = {
    "content_modified",
    "metadata_modified",
    "security_modified",
    "file_truncated",
    "allocation_modified",
}


def filesystem_result(state: dict[str, Any]) -> dict[str, Any]:
    filesystem = state["filesystem"]

    created_items = list(filesystem["created"].values())
    deleted_items = list(filesystem["deleted"].values())
    renamed_items = list(filesystem["renamed"].values())

    modified_items = _modified_items(filesystem["modified"])

    return {
        "created": collection(
            created_items,
            MAX_FILE_ITEMS,
            _created_file_groups(created_items),
            generic_item_key,
        ),
        "modified": collection(
            modified_items,
            MAX_FILE_ITEMS,
            _action_combination_groups(modified_items),
            generic_item_key,
        ),
        "deleted": collection(
            deleted_items,
            MAX_FILE_ITEMS,
            [
                *_file_groups(deleted_items, "extension"),
                *_file_groups(deleted_items, "directory_root"),
            ],
            generic_item_key,
        ),
        "renamed": collection(
            renamed_items,
            MAX_RENAME_ITEMS,
            [
                *_rename_groups(renamed_items, "destination_extension"),
                *_rename_groups(renamed_items, "extension_transition"),
                *_rename_groups(renamed_items, "same_directory"),
                *_rename_groups(renamed_items, "directory_root"),
            ],
            _rename_item_key,
            _select_rename_items,
        ),
    }


def filesystem_entity(state: dict[str, Any], path: str) -> dict[str, Any]:
    key = normalize_path(path)
    entity = state["filesystem"]["modified"].get(key)

    if entity is None:
        entity = {
            "path": path,
            "last_path": path,
            "actions": set(),
            "write_count": 0,
            "bytes_written": 0,
            "first_seen": "",
            "last_seen": "",
        }

        state["filesystem"]["modified"][key] = entity

    return entity


def file_item(path: str) -> dict[str, Any]:
    return {
        "path": path,
        "filename": _filename(path),
        "extension": extension(path),
    }


def _modified_items(entities: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    items = []

    for entity in entities.values():
        actions = set(entity["actions"])
        if not actions.intersection(FILESYSTEM_VISIBLE_ACTIONS):
            continue
        
        path = entity["path"]
        write_count = entity["write_count"]
        first_seen = entity["first_seen"]
        last_seen = entity["last_seen"]

        item = {
            "path": path,
            "actions": sorted(actions),
            "write_count": write_count,
            "first_seen": first_seen,
            "last_seen": last_seen,
        }

        if entity.get("bytes_written"):
            item["bytes_written"] = entity["bytes_written"]
        if entity.get("renamed_to"):
            item["renamed_to"] = entity["renamed_to"]

        items.append(item)

    return items


def _file_groups(
    items: Iterable[dict[str, Any]],
    group_type: str,
) -> list[dict[str, Any]]:
    counter = Counter()

    for item in items:
        path = item.get("path") or item.get("from") or ""

        if group_type == "filename":
            value = _filename(path)
        elif group_type == "extension":
            value = item.get("extension") or extension(path)
        elif group_type == "directory_root":
            value = directory_root(path)
        else:
            continue

        counter[value] += item.get("count", 1)

    groups = []
    for value, count in sorted_counter(counter):
        if not value:
            continue

        groups.append(
            {
                "type": group_type,
                "value": value,
                "count": count,
            }
        )

        if len(groups) >= MAX_GROUPS:
            break

    return groups


def _created_file_groups(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    counter = Counter()

    for item in items:
        path = item.get("path", "")
        file = item.get("filename") or _filename(path)
        file_extension = item.get("extension") or extension(path)

        if not file:
            continue

        counter[(file, file_extension)] += item.get("count", 1)

    groups = []
    for (file, file_extension), count in sorted_counter(counter):
        groups.append(
            {
                "file": file,
                "extension": file_extension,
                "count": count,
            }
        )

        if len(groups) >= MAX_GROUPS:
            break

    return groups


def _filename(path: str) -> str:
    return PureWindowsPath(path).name


def _action_combination_groups(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counter = Counter(
        tuple(item.get("actions", []))
        for item in items
    )

    groups = []
    for actions, count in sorted_counter(counter):
        groups.append(
            {
                "type": "action_combination",
                "actions": list(actions),
                "count": count,
            }
        )

        if len(groups) >= MAX_GROUPS:
            break

    return groups


def _rename_groups(
    items: Iterable[dict[str, Any]],
    group_type: str,
) -> list[dict[str, Any]]:
    counter = Counter()

    for item in items:
        if group_type == "destination_extension":
            key = item.get("destination_extension", "")
        elif group_type == "extension_transition":
            key = (item.get("source_extension", ""), item.get("destination_extension", ""))
        elif group_type == "same_directory":
            key = bool(item.get("same_directory"))
        elif group_type == "directory_root":
            key = directory_root(item.get("from", ""))
        else:
            continue

        counter[key] += item.get("count", 1)

    groups = []
    for key, count in sorted_counter(counter):
        if group_type == "extension_transition":
            groups.append(
                {
                    "type": group_type, 
                    "from": key[0], 
                    "to": key[1], 
                    "count": count,
                },
            )
        else:
            groups.append(
                {
                    "type": group_type, 
                    "value": key, 
                    "count": count,
                },
            )

    return groups[:MAX_GROUPS]


def _select_rename_items(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if len(items) <= limit:
        return items

    selected = []
    seen_ids = set()

    for field in ("destination_extension", "source_extension"):
        for item in items:
            value = item.get(field)
            identifier = _rename_item_key(item)
            marker = (field, value)

            if marker in seen_ids or identifier in seen_ids:
                continue

            selected.append(item)
            seen_ids.add(marker)
            seen_ids.add(identifier)

            if len(selected) >= limit:
                return selected

    for item in items:
        identifier = _rename_item_key(item)

        if identifier in seen_ids:
            continue

        selected.append(item)
        seen_ids.add(identifier)

        if len(selected) >= limit:
            break

    return selected


def _rename_item_key(item: dict[str, Any]) -> str:
    source = normalize_path(item.get("from", ""))
    destination = normalize_path(item.get("to", ""))

    return f"{source}|{destination}"
