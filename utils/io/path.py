import os
from pathlib import Path


def ensure_dir(path: str | os.PathLike) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def resolve_path(path: str | os.PathLike, filename: str | None = None) -> Path:
    base_path = Path(path)
    return base_path / filename if filename else base_path
