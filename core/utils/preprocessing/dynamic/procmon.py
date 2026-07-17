import copy
import json
from typing import Any

DEFAULT_PROCMON_SECTION_ORDER = (
    "processes.created",
    "processes.terminated",
    "processes.loaded_images",
    "filesystem.created",
    "filesystem.modified",
    "filesystem.deleted",
    "filesystem.renamed",
    "registry.created",
    "registry.modified",
    "registry.deleted",
    "network.connections",
    "network.dns",
)
DEFAULT_ITEMS_PER_CHUNK = 50

PROCESS_OVERVIEW_KEYS = (
    "processes_created",
    "processes_terminated",
    "images_loaded",
)
FILESYSTEM_OVERVIEW_KEYS = (
    "files_created",
    "files_modified",
    "files_deleted",
    "files_renamed",
)
REGISTRY_OVERVIEW_KEYS = (
    "registry_created",
    "registry_modified",
    "registry_deleted",
)
NETWORK_OVERVIEW_KEYS = (
    "network_connections",
    "dns_transports",
)


def prepare_procmon_sections(procmon_data: dict[str, Any]) -> list[dict[str, Any]]:
    analysis = {
        "tools": {
            "procmon": {
                "status": "ok",
                "data": procmon_data,
            }
        }
    }
    chunks = build_ai_analysis_chunks(analysis)

    return [
        {
            "type": "procmon_section",
            "tool": "procmon",
            "section": chunk["section"],
            "selected_count": _selected_count(chunk.get("data")),
            "index": chunk.get("index"),
            "total_chunks": chunk.get("total_chunks"),
            "total_items": chunk.get("total_items"),
            "value": chunk,
        }
        for chunk in chunks
    ]


def build_ai_analysis_chunks(
    analysis: dict[str, Any],
    include_empty: bool = False,
    max_chunk_characters: int = 30000,
    items_per_chunk: int = DEFAULT_ITEMS_PER_CHUNK,
    section_order: tuple[str, ...] = DEFAULT_PROCMON_SECTION_ORDER,
) -> list[dict[str, Any]]:
    procmon = _procmon_data(analysis)
    if not procmon:
        return []

    chunks = []
    for section in section_order:
        data = _section_data(procmon, section)
        if data is None:
            continue

        if not include_empty and _is_empty_section(data):
            continue

        chunks.extend(
            _section_chunks(
                procmon,
                section,
                data,
                items_per_chunk,
                max_chunk_characters,
            )
        )

    return chunks


def build_ai_procmon_input(analysis: dict[str, Any]) -> dict[str, Any]:
    procmon = _procmon_data(analysis)

    info = copy.deepcopy(procmon.get("info", {}))
    overview = copy.deepcopy(procmon.get("overview", {}))
    processes = copy.deepcopy(procmon.get("processes", {}))
    filesystem = copy.deepcopy(procmon.get("filesystem", {}))
    registry = copy.deepcopy(procmon.get("registry", {}))
    network = copy.deepcopy(procmon.get("network", {}))

    return {
        "source": "procmon",
        "data": {
            "info": info,
            "overview": overview,
            "processes": processes,
            "filesystem": filesystem,
            "registry": registry,
            "network": network,
        },
    }


def _procmon_data(analysis: dict[str, Any]) -> dict[str, Any]:
    tools = analysis.get("tools")
    if not isinstance(tools, dict):
        return {}

    procmon = tools.get("procmon")
    if not isinstance(procmon, dict):
        return {}

    data = procmon.get("data")
    return data if isinstance(data, dict) else {}


def _section_data(procmon: dict[str, Any], section: str) -> Any:
    current: Any = procmon

    for part in section.split("."):
        if not isinstance(current, dict):
            return None
        
        current = current.get(part)

    return current


def _section_chunks(
    procmon: dict[str, Any],
    section: str,
    data: Any,
    items_per_chunk: int,
    max_chunk_characters: int,
) -> list[dict[str, Any]]:
    if isinstance(data, dict) and _is_collection(data):
        return _collection_chunks(
            procmon,
            section,
            data,
            items_per_chunk,
            max_chunk_characters,
        )

    chunk = {
        "source": "procmon",
        "section": section,
        "context": _context(procmon, section),
        "data": copy.deepcopy(data),
    }
    return [_fit_chunk(chunk, max_chunk_characters)]


def _collection_chunks(
    procmon: dict[str, Any],
    section: str,
    collection: dict[str, Any],
    items_per_chunk: int,
    max_chunk_characters: int,
) -> list[dict[str, Any]]:
    items = collection.get("items")
    if not isinstance(items, list):
        items = []

    batch_size = max(1, items_per_chunk)
    batches = [
        items[index:index + batch_size]
        for index in range(0, len(items), batch_size)
    ] or [[]]

    chunks = []
    total_chunks = len(batches)
    total_items = collection.get("total", len(items))

    for index, batch in enumerate(batches, start=1):
        data = copy.deepcopy(collection)
        data["items"] = copy.deepcopy(batch)

        chunk = {
            "source": "procmon",
            "section": section,
            "context": _context(procmon, section),
            "index": index,
            "total_chunks": total_chunks,
            "total_items": total_items,
            "data": data,
        }
        chunks.append(_fit_chunk(chunk, max_chunk_characters))

    return chunks


def _context(procmon: dict[str, Any], section: str) -> dict[str, Any]:
    info = procmon.get("info", {})
    overview = procmon.get("overview", {})

    process_name = info.get("process_name", "")
    pid = info.get("pid")
    overview_subset = _overview_subset(overview, section)

    return {
        "process_name": process_name,
        "pid": pid,
        "overview": overview_subset,
    }


def _overview_subset(overview: dict[str, Any], section: str) -> dict[str, Any]:
    if section == "processes" or section.startswith("processes."):
        keys = PROCESS_OVERVIEW_KEYS
    elif section.startswith("filesystem."):
        keys = FILESYSTEM_OVERVIEW_KEYS
    elif section.startswith("registry."):
        keys = REGISTRY_OVERVIEW_KEYS
    elif section.startswith("network."):
        keys = NETWORK_OVERVIEW_KEYS
    else:
        keys = tuple(overview.keys())

    return {
        key: overview.get(key, 0)
        for key in keys
    }


def _is_empty_section(data: Any) -> bool:
    if not isinstance(data, dict):
        return False

    if _is_collection(data):
        return data.get("total", 0) == 0

    if not data:
        return True

    has_collections = False

    for value in data.values():
        if not isinstance(value, dict) or not _is_collection(value):
            continue

        has_collections = True

        if value.get("total", 0) != 0:
            return False

    return has_collections


def _is_collection(data: dict[str, Any]) -> bool:
    return (
        "total" in data
        and "truncated" in data
        and "groups" in data
        and "items" in data
    )


def _fit_chunk(chunk: dict[str, Any], max_chunk_characters: int) -> dict[str, Any]:
    if _json_size(chunk) <= max_chunk_characters:
        return chunk

    fitted = copy.deepcopy(chunk)
    data = fitted.get("data")

    if isinstance(data, dict):
        _reduce_items(data, fitted, max_chunk_characters)

    return fitted


def _reduce_items(
    data: dict[str, Any],
    chunk: dict[str, Any],
    max_chunk_characters: int,
) -> None:
    if _is_collection(data):
        _reduce_collection_items(data, chunk, max_chunk_characters)
        return

    for value in data.values():
        if isinstance(value, dict):
            _reduce_items(value, chunk, max_chunk_characters)


def _reduce_collection_items(
    collection: dict[str, Any],
    chunk: dict[str, Any],
    max_chunk_characters: int,
) -> None:
    items = collection.get("items")
    if not isinstance(items, list) or not items:
        return

    while items and _json_size(chunk) > max_chunk_characters:
        items.pop()
        chunk["input_truncated"] = True


def _json_size(data: Any) -> int:
    return len(json.dumps(data, ensure_ascii=False, default=str))


def _selected_count(data: Any) -> int:
    if isinstance(data, dict) and _is_collection(data):
        items = data.get("items")
        return len(items) if isinstance(items, list) else 0

    if isinstance(data, dict):
        total = 0
        for value in data.values():
            total += _selected_count(value)
            
        return total

    return 0
