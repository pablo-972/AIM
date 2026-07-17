from typing import Any


def prepare_registry_diff_section(
    registry_data: dict[str, Any],
) -> list[dict[str, Any]]:
    diff = registry_data.get("diff")

    if not isinstance(diff, list) or not diff:
        return []

    return [
        {
            "type": "registry_diff",
            "tool": "registry",
            "section": "diff",
            "selected_count": len(diff),
            "value": diff,
        }
    ]
