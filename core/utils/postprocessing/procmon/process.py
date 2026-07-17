import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from core.utils.postprocessing.procmon.common import (
    MAX_IMAGE_ITEMS,
    MAX_PROCESS_ITEMS,
    collection,
    normalize_path,
    normalize_row_key,
    sorted_counter,
)


def process_result(state: dict[str, Any]) -> dict[str, Any]:
    processes = state["processes"]

    created_items = list(processes["created"].values())
    terminated_items = list(processes["terminated"].values())
    loaded_images = list(processes["loaded_images"].values())

    return {
        "created": collection(
            created_items,
            MAX_PROCESS_ITEMS,
            _process_groups(created_items),
            _process_item_key,
        ),
        "terminated": collection(
            terminated_items,
            MAX_PROCESS_ITEMS,
            [],
            _generic_process_key,
        ),
        "loaded_images": collection(
            loaded_images,
            MAX_IMAGE_ITEMS,
            [],
            normalize_path,
        ),
    }


def normalize_command_line(command_line: str) -> str:
    return command_pattern(command_line).lower()


def command_line_executable(command_line: str) -> str:
    command_line = command_line.strip()

    if not command_line:
        return ""
    
    if command_line.startswith('"'):
        end = command_line.find('"', 1)
        if end > 1:
            return command_line[1:end]
        
    return command_line.split(" ", 1)[0]


def command_pattern(command_line: str) -> str:
    value = re.sub(
        r"\{[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}",
        "{GUID}",
        command_line,
    )
    return re.sub(r"\s+", " ", value).strip()


def _process_groups(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    counter = Counter()
    process_by_pattern = {}

    for item in items:
        command_line = item.get("command_line") or ""

        if not command_line:
            continue

        pattern = command_pattern(command_line)
        count = item.get("count", 1)

        process_name = item.get("process_name")
        if not process_name:
            process_name = Path(item.get("process", "")).name

        counter[pattern] += count
        process_by_pattern[pattern] = process_name

    groups = []
    for pattern, count in sorted_counter(counter):
        if count <= 1:
            continue

        groups.append(
            {
                "type": "command_pattern",
                "process": process_by_pattern[pattern],
                "pattern": pattern,
                "count": count,
            }
        )

    return groups


def _path_origin_groups(paths: Iterable[Any]) -> list[dict[str, Any]]:
    counter = Counter()

    for path in paths:
        origin = _path_origin(str(path))
        counter[origin] += 1

    groups = []
    for origin, count in sorted_counter(counter):
        groups.append(
            {
                "type": "path_origin",
                "origin": origin,
                "count": count,
            }
        )

    return groups


def _path_origin(path: str) -> str:
    value = path.lower()

    if value.startswith("\\\\"):
        return "network_path"
    if value.startswith(("c:\\windows\\system32", "c:\\windows\\syswow64", "c:\\windows\\winsxs")):
        return "windows_system"
    if value.startswith(("c:\\program files", "c:\\program files (x86)")):
        return "program_files"
    if "\\users\\" in value:
        return "user_profile"
    if "\\temp\\" in value or value.startswith("c:\\windows\\temp"):
        return "temporary"
    
    return "other"


def _generic_process_key(item: dict[str, Any]) -> str:
    keys = (
        "path",
        "from",
        "to",
        "process",
        "process_name",
        "operation",
    )

    values = []
    for key in keys:
        values.append(normalize_row_key(item.get(key)))

    return "|".join(values)


def _process_item_key(item: dict[str, Any]) -> str:
    process = normalize_row_key(item.get("process"))
    command_line = normalize_row_key(item.get("command_line"))
    pid = normalize_row_key(item.get("pid"))

    return "|".join(
        [
            process,
            command_line,
            pid,
        ]
    )
