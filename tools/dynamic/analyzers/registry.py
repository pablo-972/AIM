from pathlib import Path
from typing import Any

EXECUTABLE = "reg.exe"
OPERATION = "export"
REGISTRY_KEYS = [
    r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon",
    r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Windows",
    r"HKLM\SYSTEM\CurrentControlSet\Services",
    r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options",
    r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Browser Helper Objects",
    r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run",
    r"HKCU\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon",
]

PHASES = ("before_execution", "after_execution")


def build_registry_job(
    enabled: bool,
    timeout: int,
    collect_interval_seconds: int = 60,
) -> dict[str, Any]:
    return {
        "enabled": enabled,
        "parameters": {
            "executable": EXECUTABLE,
            "operation": OPERATION,
            "registry_keys": REGISTRY_KEYS,
            "timeout": timeout,
            "collect_interval_seconds": collect_interval_seconds,
        },
    }


def parse_registry_artifacts(path: Path) -> dict[str, Any]:
    return {
        phase: parse_registry_phase(path / phase)
        for phase in PHASES
    }


def parse_registry_phase(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}

    parsed: dict[str, dict[str, str]] = {}
    for reg_file in sorted(path.glob("*.reg")):
        parsed.update(parse_registry_file(reg_file))

    return parsed


def parse_registry_file(path: Path) -> dict[str, dict[str, str]]:
    text = _read_registry_text(path)
    current_key = None
    current_values: dict[str, str] = {}
    parsed: dict[str, dict[str, str]] = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("Windows Registry Editor"):
            continue

        if line.startswith("[") and line.endswith("]"):
            _store_registry_key(parsed, current_key, current_values)
            current_key = line[1:-1]
            current_values = {}
            continue

        if current_key and "=" in line:
            name, value = line.split("=", 1)
            current_values[_registry_value_name(name)] = value.strip()

    _store_registry_key(parsed, current_key, current_values)
    return parsed


def _store_registry_key(
    parsed: dict[str, dict[str, str]],
    key: str | None,
    values: dict[str, str],
) -> None:
    if key and values:
        parsed[key] = values


def _registry_value_name(name: str) -> str:
    name = name.strip()
    if name == "@":
        return "default"
    if len(name) >= 2 and name[0] == '"' and name[-1] == '"':
        return name[1:-1]
    return name


def _read_registry_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-16", "utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeError:
            continue
    return raw.decode("latin-1", errors="replace")
