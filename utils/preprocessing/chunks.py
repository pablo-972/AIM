import json


MAX_REPORT_JSON_SIZE = 8000


def json_size(data) -> int:
    return len(json.dumps(data, ensure_ascii=False, default=str))


def make_report_chunk(section: str, data) -> dict:
    return {
        "section": section,
        "data": data,
    }


def chunk_mapping(section: str, data: dict, chunk_size: int = MAX_REPORT_JSON_SIZE) -> list[dict]:
    chunks = []
    current = {}

    for key, value in data.items():
        candidate = dict(current)
        candidate[key] = value

        if current and json_size(candidate) > chunk_size:
            chunks.append(make_report_chunk(f"{section}.{len(chunks) + 1}", current))
            current = {key: value}
        else:
            current = candidate

        if json_size(current) > chunk_size:
            chunks.append(make_report_chunk(f"{section}.{len(chunks) + 1}", current))
            current = {}

    if current:
        chunks.append(make_report_chunk(f"{section}.{len(chunks) + 1}", current))

    return chunks


def chunk_sequence(section: str, values: list, chunk_size: int = MAX_REPORT_JSON_SIZE) -> list[dict]:
    chunks = []
    current = []

    for value in values:
        candidate = [*current, value]
        if current and json_size(candidate) > chunk_size:
            chunks.append(make_report_chunk(f"{section}.{len(chunks) + 1}", current))
            current = [value]
        else:
            current = candidate

        if json_size(current) > chunk_size:
            chunks.append(make_report_chunk(f"{section}.{len(chunks) + 1}", current))
            current = []

    if current:
        chunks.append(make_report_chunk(f"{section}.{len(chunks) + 1}", current))

    return chunks


def chunk_large_value(section: str, value) -> list[dict]:
    if json_size(value) <= MAX_REPORT_JSON_SIZE:
        return [make_report_chunk(section, value)]

    if isinstance(value, dict):
        return chunk_mapping(section, value)

    if isinstance(value, list):
        return chunk_sequence(section, value)

    return [make_report_chunk(section, str(value))]


def prepare_generic_report_chunks(tool_name: str, tool_data) -> list[dict]:
    if json_size(tool_data) <= MAX_REPORT_JSON_SIZE:
        return [tool_data]

    if isinstance(tool_data, dict):
        chunks = []
        for key, value in tool_data.items():
            chunks.extend(chunk_large_value(key, value))
        return chunks

    if isinstance(tool_data, list):
        return chunk_sequence(tool_name, tool_data)

    return chunk_large_value(tool_name, tool_data)
