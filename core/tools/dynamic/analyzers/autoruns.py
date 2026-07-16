import csv
import io
from typing import Any
from pathlib import Path

from core.utils.io.files import read_csv_text, raise_csv_field_limit

EXECUTABLE = "autorunsc.exe"
ARGUMENTS = [
    "-accepteula",
    "-nobanner",
    "-a",
    "l",
    "-c",
]

PHASES = ("before_execution", "after_execution")
AUTORUNS_FIELDS = {
    "Entry Location": "entry_location",
    "Entry": "entry",
    "Enabled": "enabled",
    "Category": "category",
    "Profile": "profile",
    "Description": "description",
    "Company": "company",
    "Image Path": "image_path",
    "Launch String": "launch_string",
}


def build_autoruns_job(
    enabled: bool,
    timeout: int,
    collect_interval_seconds: int = 60,
) -> dict[str, Any]:
    return {
        "enabled": enabled,
        "parameters": {
            "executable": EXECUTABLE,
            "arguments": ARGUMENTS,
            "timeout": timeout,
            "collect_interval_seconds": collect_interval_seconds,
        },
    }


def parse_autoruns_artifacts(path: Path) -> dict[str, Any]:
    before = parse_autoruns_csv(path / f"{PHASES[0]}.csv")
    after = parse_autoruns_csv(path / f"{PHASES[1]}.csv")

    index_entries_before = _index_entries(before)
    index_entries_after = _index_entries(after)

    diff = _diff_entries(index_entries_before, index_entries_after)

    return {
        "diff": diff
    }


def parse_autoruns_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    raise_csv_field_limit()
    entries: list[dict[str, str]] = []

    with io.StringIO(read_csv_text(path), newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            parsed = _autoruns_row(row)
            if not parsed:
                continue
            
            entry_location = parsed.get("entry_location")
            if not entry_location:
                continue

            entries.append(parsed)

    return entries


def _autoruns_row(row: dict[str, str]) -> dict[str, str]:
    parsed = {}

    for source, target in AUTORUNS_FIELDS.items():
        value = (row.get(source) or "").strip()
        if value:
            parsed[target] = value

    fields = ("entry", "image_path", "launch_string")
    if not any(parsed.get(field) for field in fields):
        return {}

    return parsed


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

        entry = after_entry or before_entry or {}

        change_type = _change_type(before_entry, after_entry)
        entry_location = entry.get("entry_location")
        entry_name = entry.get("entry")

        change = {
            "change_type": change_type,
            "entry_location": entry_location,
            "entry": entry_name,
        }

        if before_entry is None:
            after_values = _interesting_values(after_entry)
            change["values"] = after_values
        elif after_entry is None:
            before_values = _interesting_values(before_entry)
            change["values"] = before_values
        else:
            changed = _changed_values(before_entry, after_entry)
            change["values"] = changed

        changes.append(change)

    return changes


def _index_entries(values: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    indexed: dict[str, dict[str, str]] = {}

    for entry in values:
        identity = _entry_identity(entry)
        if identity:
            indexed[identity] = entry

    return indexed


def _entry_identity(entry: dict[str, str]) -> str:
    identity_fields = ("entry_location", "entry")
    fallback_fields = ("image_path", "launch_string")

    values = []
    for field in identity_fields:
        value = entry.get(field, "")
        if not value:
            continue

        values.append(value)

    if not any(values):
        for field in fallback_fields:
            value = entry.get(field, "")
            values.append(value)

    normalized_values = []
    for value in values:
        stripped_value = value.strip()
        if not stripped_value:
            continue

        normalized_values.append(stripped_value.lower())

    return "|".join(normalized_values)


def _change_type(
    before: dict[str, str] | None,
    after: dict[str, str] | None,
) -> str:
    if before is None:
        return "added"

    if after is None:
        return "removed"

    return "modified"


def _interesting_values(entry: dict[str, str] | None) -> dict[str, str]:
    if not entry:
        return {}

    fields = (
        "enabled",
        "category",
        "image_path",
        "launch_string",
        "description",
        "company",
    )

    interesting_values = {}
    for field in fields:
        value = entry.get(field)
        if not value:
            continue

        interesting_values[field] = value

    return interesting_values


def _changed_values(
    before: dict[str, str],
    after: dict[str, str],
) -> dict[str, dict[str, str | None]]:
    changes: dict[str, dict[str, str | None]] = {}
    entry_names = {"entry_location", "entry"}

    for key in sorted(set(before) | set(after)):
        if key in entry_names:
            continue

        before_value = before.get(key)
        after_value = after.get(key)

        if before_value == after_value:
            continue

        changes[key] = {
            "before": before_value,
            "after": after_value,
        }

    return changes
