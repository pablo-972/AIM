from typing import Any

from utils.preprocessing.chunks import json_size, make_report_chunk


MAX_REVERSING_EVIDENCE_SIZE = 4500


def chunk_reversing_evidence(
    section: str,
    value: Any,
    chunk_size: int = MAX_REVERSING_EVIDENCE_SIZE,
) -> list[dict[str, Any]]:
    if json_size(value) <= chunk_size:
        return [make_report_chunk(section, value)]

    if isinstance(value, dict):
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

    if isinstance(value, list):
        return _chunk_sequence(section, value, chunk_size)

    if isinstance(value, str):
        return [
            make_report_chunk(
                f"{section}.{index}",
                value[offset:offset + chunk_size],
            )
            for index, offset in enumerate(
                range(0, len(value), chunk_size),
                start=1,
            )
        ]

    return [make_report_chunk(section, str(value))]


def _chunk_sequence(
    section: str,
    values: list[Any],
    chunk_size: int,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    current: list[Any] = []

    for index, value in enumerate(values, start=1):
        if json_size(value) > chunk_size:
            if current:
                chunks.append(
                    make_report_chunk(
                        f"{section}.{len(chunks) + 1}",
                        current,
                    )
                )
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
        if current and json_size(candidate) > chunk_size:
            chunks.append(
                make_report_chunk(
                    f"{section}.{len(chunks) + 1}",
                    current,
                )
            )
            current = [value]
        else:
            current = candidate

    if current:
        chunks.append(
            make_report_chunk(
                f"{section}.{len(chunks) + 1}",
                current,
            )
        )

    return chunks
