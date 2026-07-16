from typing import Any

from core.utils.preprocessing.chunks import batched

MAX_PROCMON_ITEMS_PER_SECTION = 30

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
    max_items_per_section: int = MAX_PROCMON_ITEMS_PER_SECTION,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []

    for category, section in PROCMON_SECTIONS:
        section_values = _section_values(procmon_data, category, section)

        for section_name, values in section_values:
            if not values:
                continue

            selected_values = values[:max_items_per_section]
            batched_values = batched(selected_values, batch_size)

            for index, batch in enumerate(batched_values, start=1):
                chunks.append(
                    {
                        "type": "procmon_section_chunk",
                        "tool": "procmon",
                        "section": section_name,
                        "index": index,
                        "total_items": len(values),
                        "selected_items": len(selected_values),
                        "truncated": len(values) > len(selected_values),
                        "selection_strategy": "first_items",
                        "value": batch,
                    }
                )

    return chunks


def _section_values(
    procmon_data: dict[str, Any],
    category: str,
    section: str,
) -> list[tuple[str, list[Any]]]:
    values = procmon_data.get(category, {}).get(section, [])
    section_name = f"{category}.{section}"

    if isinstance(values, list):
        return [(section_name, values)]

    if isinstance(values, dict):
        sections = []
        
        for key, nested_values in values.items():
            if isinstance(nested_values, list):
                sections.append((f"{section_name}.{key}", nested_values))

        return sections

    return []
