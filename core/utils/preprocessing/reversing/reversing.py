from typing import Any

from core.utils.chunks import json_size, make_report_chunk

MAX_REVERSING_EVIDENCE_SIZE = 4500
MAX_DISASSEMBLY_INSTRUCTIONS_PER_CHUNK = 24


def chunk_reversing_evidence(
    section: str,
    value: Any,
    chunk_size: int = MAX_REVERSING_EVIDENCE_SIZE,
) -> list[dict[str, Any]]:
    disassembly_chunks = _chunk_disassembly_instructions(section, value)
    if disassembly_chunks:
        return disassembly_chunks

    if _fits_in_chunk(value, chunk_size):
        return [make_report_chunk(section, value)]

    if isinstance(value, dict):
        return _chunk_mapping(section, value, chunk_size)

    if isinstance(value, list):
        return _chunk_sequence(section, value, chunk_size)

    if isinstance(value, str):
        return _chunk_text(section, value, chunk_size)

    return [make_report_chunk(section, str(value))]


def _chunk_disassembly_instructions(
    section: str,
    value: Any,
) -> list[dict[str, Any]]:
    if section != "disassembly" or not isinstance(value, dict):
        return []

    instructions = value.get("instructions")
    if not _is_instruction_lines(instructions):
        return []

    chunks = []
    lines = list(instructions)
    
    for offset in range(0, len(lines), MAX_DISASSEMBLY_INSTRUCTIONS_PER_CHUNK):
        chunk_lines = lines[offset:offset + MAX_DISASSEMBLY_INSTRUCTIONS_PER_CHUNK]
        chunks.append(
            make_report_chunk(
                f"{section}.instructions.{len(chunks) + 1}",
                "\n".join(chunk_lines),
            )
        )

    return chunks


def _is_instruction_lines(value: Any) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(item, str) for item in value)
    )


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
