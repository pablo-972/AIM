from typing import Any


SOURCE_PHASES = (
    "static",
    "dynamic",
    "enrichment",
    "reversing",
)


def group_sources_by_phase(
    sources: list[tuple[str, Any]],
) -> list[tuple[str, dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {
        phase: []
        for phase in SOURCE_PHASES
    }

    for source_name, source_data in sources:
        phase = _source_phase(source_name)
        grouped[phase].append(
            {
                "source": source_name,
                "data": source_data,
            }
        )

    result = []
    for phase, items in grouped.items():
        if not items:
            continue

        result.append(
            (
                phase,
                {
                    "phase": phase,
                    "source_count": len(items),
                    "sources": items,
                },
            )
        )

    return result


def _source_phase(source_name: str) -> str:
    if source_name.startswith("dynamic.") or source_name.startswith("dynamic_"):
        return "dynamic"

    if source_name.startswith("reversing"):
        return "reversing"

    if source_name.startswith("reverse_engineering"):
        return "enrichment"

    return "static"
