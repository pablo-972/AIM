import json

import yaml

from utils.logger import Logger
from utils.io.path import resolve_path, ensure_dir


def save_json(path: str, filename: str, data: dict):
    output_path = resolve_path(path, filename)
    ensure_dir(output_path.parent)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

    Logger.success(f"JSON data saved to {output_path}")


def load_json(path: str, filename: str):
    output_path = resolve_path(path, filename)
    if not output_path.exists():
        return None
    
    with open(output_path, "r", encoding="utf-8", errors="replace") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return None


def load_yaml(path: str, filename: str):
    output_path = resolve_path(path, filename)
    if not output_path.exists():
        return None
    
    with open(output_path, "r", encoding="utf-8", errors="replace") as file:
        try:
            return yaml.safe_load(file)
        except yaml.YAMLError:
            return None



















