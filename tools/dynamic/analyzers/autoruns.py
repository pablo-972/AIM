import csv
import io
import sys
from typing import Any
from pathlib import Path

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

    _raise_csv_field_limit()
    entries: list[dict[str, str]] = []

    with io.StringIO(_read_csv_text(path), newline="") as file:
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


def _read_csv_text(path: Path) -> str:
    raw = path.read_bytes()
    encoders = ("utf-16", "utf-8-sig", "latin-1")

    for encoding in encoders:
        try:
            return raw.decode(encoding)
        except UnicodeError:
            continue

    return raw.decode("latin-1", errors="replace")


def _raise_csv_field_limit() -> None:
    limit = sys.maxsize

    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit = int(limit / 10)
