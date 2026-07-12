from typing import Any

from utils.preprocessing.chunks import batched

PHASE_BEFORE = "before_execution"
PHASE_AFTER = "after_execution"
ENTRY_FIELD = "Entry"


def prepare_registry_diff_chunks(
    registry_data: dict[str, Any],
    batch_size: int = 5,
) -> list[dict[str, Any]]:
    before = _index_entries(registry_data.get(PHASE_BEFORE, []))
    after = _index_entries(registry_data.get(PHASE_AFTER, []))
    changes = _diff_entries(before, after)

    return [
        {
            "type": "registry_diff_chunk",
            "tool": "registry",
            "section": "diff",
            "index": index,
            "value": batch,
        }
        for index, batch in enumerate(batched(changes, batch_size), start=1)
    ]


def _diff_entries(
    before: dict[str, dict[str, str]],
    after: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []

    for entry in sorted(set(before) | set(after)):
        before_entry = before.get(entry)
        after_entry = after.get(entry)

        if before_entry == after_entry:
            continue

        if before_entry is None:
            changes.append(
                {
                    "change_type": "added",
                    "Entry": entry,
                    "before": None,
                    "after": after_entry,
                    "values": _values(after_entry),
                }
            )
        elif after_entry is None:
            changes.append(
                {
                    "change_type": "removed",
                    "Entry": entry,
                    "before": before_entry,
                    "after": None,
                    "values": _values(before_entry),
                }
            )
        else:
            changes.append(
                {
                    "change_type": "modified",
                    "Entry": entry,
                    "before": before_entry,
                    "after": after_entry,
                    "values": _changed_values(before_entry, after_entry),
                }
            )

    return changes


def _index_entries(values: Any) -> dict[str, dict[str, str]]:
    if not isinstance(values, list):
        return {}

    indexed: dict[str, dict[str, str]] = {}

    for entry in values:
        if not isinstance(entry, dict):
            continue

        entry_name = entry.get(ENTRY_FIELD)
        if not isinstance(entry_name, str) or not entry_name:
            continue

        normalized_entry = {}
        for key, value in entry.items():
            if value is None:
                continue

            normalized_entry[str(key)] = str(value)

        indexed[entry_name] = normalized_entry

    return indexed


def _values(entry: dict[str, str] | None) -> dict[str, str]:
    if not entry:
        return {}

    values = {}

    for key, value in entry.items():
        if key == ENTRY_FIELD:
            continue

        values[key] = value

    return values


def _changed_values(
    before: dict[str, str],
    after: dict[str, str],
) -> dict[str, dict[str, str | None]]:
    changes: dict[str, dict[str, str | None]] = {}
    before_values = _values(before)
    after_values = _values(after)

    for key in sorted(set(before_values) | set(after_values)):
        before_value = before_values.get(key)
        after_value = after_values.get(key)

        if before_value == after_value:
            continue

        changes[key] = {
            "before": before_value,
            "after": after_value,
        }

    return changes
