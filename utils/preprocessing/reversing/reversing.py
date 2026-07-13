from typing import Any

from utils.preprocessing.chunks import json_size, make_report_chunk

MAX_REVERSING_EVIDENCE_SIZE = 4500


def chunk_reversing_evidence(
    section: str,
    value: Any,
    chunk_size: int = MAX_REVERSING_EVIDENCE_SIZE,
) -> list[dict[str, Any]]:
    if _fits_in_chunk(value, chunk_size):
        return [make_report_chunk(section, value)]

    if isinstance(value, dict):
        return _chunk_mapping(section, value, chunk_size)

    if isinstance(value, list):
        return _chunk_sequence(section, value, chunk_size)

    if isinstance(value, str):
        return _chunk_text(section, value, chunk_size)

    return [make_report_chunk(section, str(value))]


def _fits_in_chunk(value: Any, chunk_size: int) -> bool:
    return json_size(value) <= chunk_size


def _numbered_section(section: str, chunks: list[dict[str, Any]]) -> str:
    return f"{section}.{len(chunks) + 1}"


def _append_chunk(
    chunks: list[dict[str, Any]],
    section: str,
    value: Any,
) -> None:
    chunks.append(
        make_report_chunk(
            _numbered_section(section, chunks),
            value,
        )
    )


def _chunk_mapping(
    section: str,
    value: dict[str, Any],
    chunk_size: int,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []

    for key, item in value.items():
        chunks.extend(
            chunk_reversing_evidence(
                f"{section}.{key}",
                item,
                chunk_size,
            )
        )

    return chunks


def _chunk_text(
    section: str,
    value: str,
    chunk_size: int,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    offset = 0

    while offset < len(value):
        length = _max_text_length_for_chunk(
            section=_numbered_section(section, chunks),
            value=value,
            offset=offset,
            chunk_size=chunk_size,
        )

        _append_chunk(
            chunks,
            section,
            value[offset:offset + length],
        )

        offset += length

    return chunks


def _max_text_length_for_chunk(
    section: str,
    value: str,
    offset: int,
    chunk_size: int,
) -> int:
    low = 1
    high = min(chunk_size, len(value) - offset)
    accepted = 1

    while low <= high:
        length = (low + high) // 2
        candidate = make_report_chunk(
            section,
            value[offset:offset + length],
        )

        if _fits_in_chunk(candidate, chunk_size):
            accepted = length
            low = length + 1
        else:
            high = length - 1

    return accepted


def _chunk_sequence(
    section: str,
    values: list[Any],
    chunk_size: int,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    current: list[Any] = []

    for index, value in enumerate(values, start=1):
        if not _fits_in_chunk(value, chunk_size):
            _flush_current(chunks, section, current)
            current = []

            chunks.extend(
                chunk_reversing_evidence(
                    f"{section}.item_{index}",
                    value,
                    chunk_size,
                )
            )
            continue

        candidate = [*current, value]

        if current and not _fits_in_chunk(candidate, chunk_size):
            _append_chunk(chunks, section, current)
            current = [value]
        else:
            current = candidate

    _flush_current(chunks, section, current)

    return chunks


def _flush_current(
    chunks: list[dict[str, Any]],
    section: str,
    current: list[Any],
) -> None:
    if current:
        _append_chunk(chunks, section, current)
