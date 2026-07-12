from typing import Any

from utils.preprocessing.chunks import batched

PHASE_BEFORE = "before_execution"
PHASE_AFTER = "after_execution"
IDENTITY_FIELDS = ("entry_location", "entry")
FALLBACK_IDENTITY_FIELDS = ("image_path", "launch_string")


def prepare_autoruns_diff_chunks(
    autoruns_data: dict[str, Any],
    batch_size: int = 5,
) -> list[dict[str, Any]]:
    before = _index_entries(autoruns_data.get(PHASE_BEFORE, []))
    after = _index_entries(autoruns_data.get(PHASE_AFTER, []))
    changes = _diff_entries(before, after)

    return [
        {
            "type": "autoruns_diff_chunk",
            "tool": "autoruns",
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

    for key in sorted(set(before) | set(after)):
        before_entry = before.get(key)
        after_entry = after.get(key)

        if before_entry == after_entry:
            continue

        if before_entry is None:
            entry_location = None
            if after_entry:
                entry_location = after_entry.get("entry_location")

            changes.append(
                {
                    "change_type": "added",
                    "entry_location": entry_location,
                    "before": None,
                    "after": after_entry,
                }
            )
        elif after_entry is None:
            entry_location = None
            if before_entry:
                entry_location = before_entry.get("entry_location")

            changes.append(
                {
                    "change_type": "removed",
                    "entry_location": entry_location,
                    "before": before_entry,
                    "after": None,
                }
            )
        else:
            entry_location = (
                after_entry.get("entry_location") 
                or before_entry.get("entry_location")
            )

            changes.append(
                {
                    "change_type": "modified",
                    "entry_location": entry_location,
                    "before": before_entry,
                    "after": after_entry,
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
        
        normalized = {}
        for key, value in entry.items():
            if value is None:
                continue
                
            normalized[str(key)] = str(value)

        identity = _entry_identity(normalized)
        if identity:
            indexed[identity] = normalized

    return indexed


def _entry_identity(entry: dict[str, str]) -> str:
    values = []

    for field in IDENTITY_FIELDS:
        values.append(entry.get(field, ""))

    if not any(values):
        values = []

        for field in FALLBACK_IDENTITY_FIELDS:
            values.append(entry.get(field, ""))

    normalized_values = []

    for value in values:
        value = value.strip().lower()
        if value:
            normalized_values.append(value)

    return "|".join(normalized_values)
