import re
from dataclasses import dataclass


SHARED_FOLDER_KEY = re.compile(
    r"^SharedFolder"
    r"(Name|Path|Writable|AutoMount|AutoMountPoint)"
    r"MachineMapping"
    r"(\d+)$"
)


@dataclass(frozen=True)
class SharedFolder:
    name: str
    hostpath: str
    readonly: bool
    automount: bool
    mount_point: str | None


def parse_running_vm_names(stdout: str) -> list[str]:
    names: list[str] = []

    for line in stdout.splitlines():
        if not line.startswith('"'):
            continue

        end = line.find('"', 1)
        if end > 1:
            names.append(line[1:end])

    return names


def parse_shared_folder(stdout: str, folder_name: str) -> SharedFolder | None:
    mappings: dict[str, dict[str, str]] = {}

    for line in stdout.splitlines():
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        match = SHARED_FOLDER_KEY.match(key)
        if match is None:
            continue

        field, index = match.groups()
        mapping = mappings.setdefault(index, {})
        mapping[field] = value.strip('"')

    for mapping in mappings.values():
        if mapping.get("Name") != folder_name:
            continue

        hostpath = mapping.get("Path")
        if not hostpath:
            return None

        mount_point = mapping.get("AutoMountPoint") or None
        return SharedFolder(
            name=folder_name,
            hostpath=hostpath,
            readonly=not _parse_bool(mapping.get("Writable"), default=True),
            automount=_parse_bool(mapping.get("AutoMount"), default=False),
            mount_point=mount_point,
        )

    return None


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default

    return value.lower() in {"1", "true", "yes", "on"}
