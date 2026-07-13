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
    artifacts: dict[str, Any] = {}

    for phase in PHASES:
        csv_path = path / f"{phase}.csv"
        artifacts[phase] = parse_autoruns_csv(csv_path)

    return artifacts


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
