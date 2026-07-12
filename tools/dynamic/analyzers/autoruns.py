import csv
import io
from pathlib import Path
import sys
from typing import Any

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
    return {
        phase: parse_autoruns_csv(path / f"{phase}.csv")
        for phase in PHASES
    }


def parse_autoruns_csv(path: Path) -> dict[str, list[dict[str, str]]]:
    if not path.exists():
        return {}

    _raise_csv_field_limit()
    entries: dict[str, list[dict[str, str]]] = {}
    with io.StringIO(_read_csv_text(path), newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            parsed = _autoruns_row(row)
            if not parsed:
                continue

            entry_location = parsed.pop("entry_location", "")
            if not entry_location:
                continue

            entries.setdefault(entry_location, []).append(parsed)

    return entries


def _autoruns_row(row: dict[str, str]) -> dict[str, str]:
    parsed = {}
    for source, target in AUTORUNS_FIELDS.items():
        value = (row.get(source) or "").strip()
        if value:
            parsed[target] = value

    if not any(parsed.get(field) for field in ("entry", "image_path", "launch_string")):
        return {}

    return parsed


def _read_csv_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-16", "utf-8-sig", "latin-1"):
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
