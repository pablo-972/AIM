import json
import os
from pathlib import Path
from typing import Any

import yaml

from exceptions import FileReadError


def ensure_dir(path: str | Path) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def save_json(path: str | Path, filename: str, data: dict[str, Any]) -> None:
    directory = Path(path)
    ensure_dir(directory)

    target = directory / filename
    tmp = target.with_suffix(target.suffix + ".tmp")

    with tmp.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    os.replace(tmp, target)


def load_json(
    path: str | Path,
    filename: str | Path,
) -> dict[str, Any] | None:
    target = Path(path) / filename
    if not target.exists():
        return None

    try:
        with target.open("r", encoding="utf-8") as file:
            data = json.load(file)
            if not isinstance(data, dict):
                raise FileReadError(f"JSON root must be an object: {target}")
            return data
    except json.JSONDecodeError as exc:
        raise FileReadError(f"Invalid JSON file: {target}") from exc


def load_yaml(
    path: str | Path,
    filename: str | Path,
) -> dict[str, Any] | None:
    target = Path(path) / filename if path else Path(filename)
    if not target.exists():
        return None

    try:
        with target.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
            if data is None:
                return None
            if not isinstance(data, dict):
                raise FileReadError(f"YAML root must be an object: {target}")
            return data
    except yaml.YAMLError as exc:
        raise FileReadError(f"Invalid YAML file: {target}") from exc



















