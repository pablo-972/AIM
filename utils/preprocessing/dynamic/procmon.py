from typing import Any

from utils.preprocessing.chunks import batched

PROCMON_SECTIONS = (
    ("processes", "created"),
    ("processes", "terminated"),
    ("processes", "loaded_images"),
    ("filesystem", "created"),
    ("filesystem", "modified"),
    ("filesystem", "deleted"),
    ("filesystem", "renamed"),
    ("registry", "created"),
    ("registry", "modified"),
    ("registry", "deleted"),
    ("network", "dns"),
    ("network", "tcp"),
    ("network", "udp"),
)


def prepare_procmon_chunks(
    procmon_data: dict[str, Any],
    batch_size: int = 5,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []

    for category, section in PROCMON_SECTIONS:
        values = procmon_data.get(category, {}).get(section, [])
        if not isinstance(values, list) or not values:
            continue

        section_name = f"{category}.{section}"

        for index, batch in enumerate(batched(values, batch_size), start=1):
            chunks.append(
                {
                    "type": "procmon_section_chunk",
                    "tool": "procmon",
                    "section": section_name,
                    "index": index,
                    "value": batch,
                }
            )

    return chunks
