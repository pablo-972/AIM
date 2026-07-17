import json
from typing import Any


MAX_REPORT_JSON_SIZE = 8000


def json_size(data: Any) -> int:
    return len(json.dumps(data, ensure_ascii=False, default=str))


def make_report_chunk(section: str, data: Any) -> dict[str, Any]:
    return {
        "section": section,
        "data": data,
    }


def batched(values: list[Any], batch_size: int) -> list[list[Any]]:
    size = max(1, batch_size)
    batches = []

    for index in range(0, len(values), size):
        batch = values[index:index + size]
        batches.append(batch)

    return batches


def chunk_mapping(
    section: str,
    data: dict[str, Any],
    chunk_size: int = MAX_REPORT_JSON_SIZE,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    current: dict[str, Any] = {}

    for key, value in data.items():
        candidate = {**current, key: value}

        if current and json_size(candidate) > chunk_size:
            _append_numbered_chunk(chunks, section, current)
            current = {key: value}
        else:
            current = candidate

        if json_size(current) > chunk_size:
            _append_numbered_chunk(chunks, section, current)
            current = {}

    if current:
        _append_numbered_chunk(chunks, section, current)

    return chunks


def chunk_sequence(
    section: str,
    values: list[Any],
    chunk_size: int = MAX_REPORT_JSON_SIZE,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    current: list[Any] = []

    for value in values:
        candidate = [*current, value]

        if current and json_size(candidate) > chunk_size:
            _append_numbered_chunk(chunks, section, current)
            current = [value]
        else:
            current = candidate

        if json_size(current) > chunk_size:
            _append_numbered_chunk(chunks, section, current)
            current = []

    if current:
        _append_numbered_chunk(chunks, section, current)

    return chunks


def chunk_large_value(section: str, value: Any) -> list[dict[str, Any]]:
    if json_size(value) <= MAX_REPORT_JSON_SIZE:
        return [make_report_chunk(section, value)]

    if isinstance(value, dict):
        return chunk_mapping(section, value)

    if isinstance(value, list):
        return chunk_sequence(section, value)

    return [make_report_chunk(section, str(value))]


def prepare_generic_report_chunks(tool_name: str, tool_data: Any) -> list[Any]:
    if json_size(tool_data) <= MAX_REPORT_JSON_SIZE:
        return [make_report_chunk(tool_name, tool_data)]

    if isinstance(tool_data, dict):
        chunks: list[dict[str, Any]] = []
        for key, value in tool_data.items():
            chunks.extend(chunk_large_value(key, value))
            
        return chunks

    if isinstance(tool_data, list):
        return chunk_sequence(tool_name, tool_data)

    return chunk_large_value(tool_name, tool_data)


def _append_numbered_chunk(
    chunks: list[dict[str, Any]],
    section: str,
    data: Any,
) -> None:
    chunks.append(
        make_report_chunk(
            f"{section}.{len(chunks) + 1}",
            data,
        )
    )
