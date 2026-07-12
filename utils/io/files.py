import csv
import json
import os
import sys
from typing import Any
from pathlib import Path

import yaml

from exceptions import FileReadError


def ensure_dir(path: str | Path) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def save_json(path: str | Path, filename: str, data: dict[str, Any]) -> None:
    directory = Path(path)
    ensure_dir(directory)

    target = directory / filename
    tmp_path = target.with_suffix(target.suffix + ".tmp")

    with tmp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    os.replace(tmp_path, target)


def save_pmc(path: str | Path, filename: str, data: bytes | str) -> None:
    directory = Path(path)
    ensure_dir(directory)

    target = directory / filename
    tmp_path = target.with_suffix(target.suffix + ".tmp")
    raw_data = data.encode("utf-8") if isinstance(data, str) else data

    with tmp_path.open("wb") as file:
        file.write(raw_data)

    os.replace(tmp_path, target)


def load_json(path: str | Path, filename: str | Path) -> dict[str, Any] | None:
    target = Path(path) / filename
    if not target.exists():
        return None

    try:
        with target.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise FileReadError(f"Invalid JSON file: {target}") from exc
    
    if not isinstance(data, dict):
        raise FileReadError(f"JSON root must be an object: {target}")
    
    return data


def load_yaml(path: str | Path, filename: str | Path) -> dict[str, Any] | None:
    target = Path(path) / filename if path else Path(filename)
    if not target.exists():
        return None

    try:
        with target.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
    except yaml.YAMLError as exc:
        raise FileReadError(f"Invalid YAML file: {target}") from exc
    
    if not isinstance(data, dict):
        raise FileReadError(f"YAML root must be an object: {target}")
    
    if data is None:
        return None

    return data


def read_csv_text(path: str | Path) -> str:
    raw = Path(path).read_bytes()
    encoders = ("utf-16", "utf-8-sig", "latin-1")

    for encoding in encoders:
        try:
            return raw.decode(encoding)
        except UnicodeError:
            continue

    return raw.decode("latin-1", errors="replace")


def raise_csv_field_limit() -> None:
    limit = sys.maxsize

    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit = int(limit / 10)
















