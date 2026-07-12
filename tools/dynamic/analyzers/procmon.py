import csv
import io
from pathlib import Path
import re
import sys
from typing import Any

EXECUTABLE = "procmon.exe"
START_ARGUMENTS = [
    "/AcceptEula",
    "/Quiet",
    "/BackingFile",
    "procmon.pml",
]
STOP_ARGUMENTS = [
    "/Terminate",
]
SAVE_ARGUMENTS = [
    "/AcceptEula",
    "/Quiet",
    "/OpenLog",
    "{pml_path}",
    "/SaveAs",
    "{csv_path}",
]

STOP_WAIT_SECONDS = 30
SAVE_WAIT_SECONDS = 30

BACKING_FILE = "procmon.pml"
CSV_FILE = "procmon.csv"


def build_procmon_job(
    enabled: bool,
    timeout: int,
    collect_interval_seconds: int = 60,
    filter_config: str | None = None,
) -> dict[str, Any]:
    start_arguments = list(START_ARGUMENTS)
    save_arguments = list(SAVE_ARGUMENTS)

    if filter_config:
        start_arguments = [
            "/AcceptEula",
            "/Quiet",
            "/LoadConfig",
            "{filter_config_path}",
            "/BackingFile",
            BACKING_FILE,
        ]
        save_arguments.append("/SaveApplyFilter")

    parameters = {
        "executable": EXECUTABLE,
        "start_arguments": start_arguments,
        "stop_arguments": STOP_ARGUMENTS,
        "save_arguments": save_arguments,
        "backing_file": BACKING_FILE,
        "csv_file": CSV_FILE,
        "stop_wait_seconds": STOP_WAIT_SECONDS,
        "save_wait_seconds": SAVE_WAIT_SECONDS,
        "timeout": timeout,
        "collect_interval_seconds": collect_interval_seconds,
    }
    
    if filter_config:
        parameters["filter_config"] = filter_config

    return {
        "enabled": enabled,
        "parameters": parameters,
    }


def parse_procmon_artifacts(path: Path, sample: Path) -> dict[str, Any]:
    csv_path = path / CSV_FILE
    sample_process_names = _sample_process_names(sample)

    return {
        "events": parse_procmon_csv(csv_path, sample_process_names),
    }


def parse_procmon_csv(path: Path, process_names: set[str]) -> list[dict[str, str]]:
    if not path.exists():
        return []

    _raise_csv_field_limit()
    events: list[dict[str, str]] = []
    with io.StringIO(_read_csv_text(path), newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            parsed = {
                _normalize_field_name(key): (value or "").strip()
                for key, value in row.items()
                if key
            }

            process_name = parsed.get("process_name", "").lower()
            if process_name not in process_names:
                continue

            events.append(parsed)

    return events


def _sample_process_names(sample: Path) -> set[str]:
    process_names = {sample.name.lower()}
    if sample.suffix.lower() == ".exe":
        process_names.add(sample.name.lower())
    else:
        process_names.add((sample.stem + ".exe").lower())
        process_names.add((sample.name + ".exe").lower())

    return process_names


def _normalize_field_name(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


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
