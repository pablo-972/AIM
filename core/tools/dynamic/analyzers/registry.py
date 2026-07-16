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
    before = parse_registry_phase(path / PHASES[0])
    after = parse_registry_phase(path / PHASES[1])

    return {
        "diff": _diff_entries(
            _index_entries(before),
            _index_entries(after),
        )
    }


def parse_registry_phase(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    parsed: list[dict[str, str]] = []
    for reg_file in sorted(path.glob("*.reg")):
        parsed_reg_file = parse_registry_file(reg_file)
        parsed.extend(parsed_reg_file)

    return parsed


def parse_registry_file(path: Path) -> list[dict[str, str]]:
    text = _read_registry_text(path)
    current_key = None
    current_values: dict[str, str] = {}
    parsed: list[dict[str, str]] = []

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
            registry_name = _registry_value_name(name)
            current_values[registry_name] = value.strip()

    _store_registry_key(parsed, current_key, current_values)
    return parsed


def _store_registry_key(
    parsed: list[dict[str, str]],
    key: str | None,
    values: dict[str, str],
) -> None:
    if key and values:
        entry = {"Entry": key}
        entry.update(values)
        parsed.append(entry)


def _registry_value_name(name: str) -> str:
    name = name.strip()

    if name == "@":
        return "default"
    
    if len(name) >= 2 and name[0] == '"' and name[-1] == '"':
        return name[1:-1]
    
    return name


def _read_registry_text(path: Path) -> str:
    raw = path.read_bytes()
    encoders = ("utf-16", "utf-8-sig", "latin-1")

    for encoding in encoders:
        try:
            return raw.decode(encoding)
        except UnicodeError:
            continue
        
    return raw.decode("latin-1", errors="replace")


def _diff_entries(
    before: dict[str, dict[str, str]],
    after: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []

    for entry in sorted(set(before) | set(after)):
        before_entry = before.get(entry)
        after_entry = after.get(entry)

        if before_entry == after_entry:
            continue

        if before_entry is None:
            changes.append(
                {
                    "change_type": "added",
                    "Entry": entry,
                    "values": _values(after_entry),
                }
            )
        elif after_entry is None:
            changes.append(
                {
                    "change_type": "removed",
                    "Entry": entry,
                    "values": _values(before_entry),
                }
            )
        else:
            changes.append(
                {
                    "change_type": "modified",
                    "Entry": entry,
                    "values": _changed_values(before_entry, after_entry),
                }
            )

    return changes


def _index_entries(values: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    indexed: dict[str, dict[str, str]] = {}

    for entry in values:
        entry_name = entry.get("Entry")
        if not entry_name:
            continue

        if _contains_procmon(entry):
            continue

        indexed[entry_name] = entry

    return indexed


def _contains_procmon(entry: dict[str, str]) -> bool:
    for key, value in entry.items():
        if "procmon" in str(key).lower():
            return True

        if "procmon" in str(value).lower():
            return True

    return False


def _values(entry: dict[str, str] | None) -> dict[str, str]:
    if not entry:
        return {}

    return {
        key: value
        for key, value in entry.items()
        if key != "Entry"
    }


def _changed_values(
    before: dict[str, str],
    after: dict[str, str],
) -> dict[str, dict[str, str | None]]:
    changes: dict[str, dict[str, str | None]] = {}
    before_values = _values(before)
    after_values = _values(after)

    for key in sorted(set(before_values) | set(after_values)):
        before_value = before_values.get(key)
        after_value = after_values.get(key)

        if before_value == after_value:
            continue

        changes[key] = {
            "before": before_value,
            "after": after_value,
        }

    return changes
