from typing import Any


def prepare_autoruns_diff_section(
    autoruns_data: dict[str, Any],
) -> list[dict[str, Any]]:
    diff = autoruns_data.get("diff")

    if not isinstance(diff, list) or not diff:
        return []

    return [
        {
            "type": "autoruns_diff",
            "tool": "autoruns",
            "section": "diff",
            "selected_count": len(diff),
            "value": diff,
        }
    ]
