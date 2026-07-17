import csv
import io
import re
from collections import Counter
from pathlib import Path
from typing import Any

from core.utils.io.files import read_csv_text, raise_csv_field_limit
from core.utils.postprocessing.procmon import (
    command_line_executable,
    directory,
    dns_item,
    extension,
    file_item,
    filesystem_entity,
    finalize_procmon_state,
    merge_item,
    network_item,
    normalize_command_line,
    normalize_path,
    registry_item,
    update_connection_counts,
    update_dns_counts,
    update_info_local_address,
)

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

SUCCESS_RESULTS = {"SUCCESS"}

PROCESS_CREATED_OPERATIONS = {"Process Create"}
PROCESS_TERMINATED_OPERATIONS = {"Process Exit"}
PROCESS_IMAGE_OPERATIONS = {"Load Image"}

FILESYSTEM_CREATED_OPERATIONS = {"CreateFile", "CreateDirectory"}
CONTENT_MODIFICATION_OPERATIONS = {"WriteFile"}
METADATA_MODIFICATION_OPERATIONS = {"SetBasicInformationFile"}
SECURITY_MODIFICATION_OPERATIONS = {"SetSecurityFile"}
TRUNCATION_OPERATIONS = {"SetEndOfFileInformationFile"}
ALLOCATION_MODIFICATION_OPERATIONS = {"SetAllocationInformationFile"}
FILESYSTEM_DELETED_OPERATIONS = {
    "SetDispositionInformationFile",
    "SetDispositionInformationEx",
    "SetDispositionInformationFileEx",
    "DeleteFile",
}
FILESYSTEM_RENAMED_OPERATIONS = {
    "SetRenameInformationFile",
    "SetRenameInformationEx",
    "SetRenameInformationFileEx",
}

REGISTRY_CREATED_OPERATIONS = {"RegCreateKey"}
REGISTRY_MODIFIED_OPERATIONS = {
    "RegSetValue",
    "RegSetKeySecurity",
    "RegSetInformationKey",
    "RegRestoreKey",
    "RegReplaceKey",
    "RegLoadKey",
    "RegUnloadKey",
}
REGISTRY_DELETED_OPERATIONS = {"RegDeleteKey", "RegDeleteValue"}

TCP_OPERATIONS = {
    "TCP Connect",
    "TCP Reconnect",
    "TCP Accept",
    "TCP Send",
    "TCP Receive",
    "TCP Disconnect",
    "TCP TCPCopy",
}
UDP_OPERATIONS = {"UDP Send", "UDP Receive"}

SERVICE_PORTS = {
    "domain": 53,
    "dns": 53,
    "http": 80,
    "https": 443,
    "microsoft-ds": 445,
    "netbios-ssn": 139,
}


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
    return parse_procmon_csv(csv_path, _sample_process_names(sample))


def parse_procmon_csv(path: Path, process_names: set[str]) -> dict[str, Any]:
    state = _new_state()

    if not path.exists():
        return finalize_procmon_state(state)

    raise_csv_field_limit()

    with io.StringIO(read_csv_text(path), newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            event = _normalize_row(row)
            if not _is_successful_event(event):
                continue
            if not _should_process_event(state, event, process_names):
                continue

            _record_operation_statistics(state, event)
            _update_info(state, event)
            _record_process_event(state, event)
            _record_filesystem_event(state, event)
            _record_registry_event(state, event)
            _record_network_event(state, event)

    return finalize_procmon_state(state)


def _is_successful_event(event: dict[str, str]) -> bool:
    result = event.get("result", "")
    return result in SUCCESS_RESULTS


def _record_operation_statistics(
    state: dict[str, Any],
    event: dict[str, str],
) -> None:
    operation = event.get("operation", "")
    if operation:
        state["operation_statistics"][operation] += 1


def _new_state() -> dict[str, Any]:
    return {
        "info": {
            "process_name": "",
            "pid": None,
            "local_address": "",
        },
        "tracked_pids": set(),
        "processes": {
            "created": {},
            "terminated": {},
            "loaded_images": {},
        },
        "filesystem": {
            "created": {},
            "modified": {},
            "deleted": {},
            "renamed": {},
        },
        "registry": {
            "created": {},
            "modified": {},
            "deleted": {},
        },
        "network": {
            "connections": {},
            "dns": {},
        },
        "operation_statistics": Counter(),
    }


def _normalize_row(row: dict[str, str]) -> dict[str, str]:
    parsed = {}

    for key, value in row.items():
        if not key:
            continue
        
        normalized_field_name = _normalize_field_name(key)
        parsed[normalized_field_name] = (value or "").strip()

    return parsed


def _should_process_event(
    state: dict[str, Any],
    event: dict[str, str],
    process_names: set[str],
) -> bool:
    tracked_pids = state["tracked_pids"]

    pid = _int_or_none(event.get("pid", ""))
    process_name = event.get("process_name", "").lower()

    name_match = process_name in process_names
    pid_match = pid is not None and pid in tracked_pids

    if name_match and pid is not None:
        tracked_pids.add(pid)

    detail = event.get("detail", "")
    parent_pid = _int_or_none(_detail_value(detail, "Parent PID")) or pid
    child_pid = _process_child_pid(detail)
    parent_match = parent_pid is not None and parent_pid in tracked_pids

    is_process_create = event.get("operation") in PROCESS_CREATED_OPERATIONS
    should_track_child = is_process_create and (
        name_match or pid_match or parent_match
    )

    if should_track_child:
        if child_pid is not None:
            tracked_pids.add(child_pid)

        return True

    return name_match or pid_match


def _update_info(state: dict[str, Any], event: dict[str, str]) -> None:
    info = state["info"]

    event_pid = _int_or_none(event.get("pid", ""))
    event_process_name = event.get("process_name", "")

    if not info["process_name"] and event_process_name:
        info["process_name"] = event_process_name

    if info["pid"] is None and event_pid is not None:
        info["pid"] = event_pid


def _record_process_event(state: dict[str, Any], event: dict[str, str]) -> None:
    operation = event.get("operation", "")

    if operation in PROCESS_CREATED_OPERATIONS:
        detail = event.get("detail", "")
        path = event.get("path", "")
        
        command_line = _detail_value(detail, "Command line")
        image_path = _detail_value(detail, "Image Path") or path
        child_pid = _process_child_pid(detail)

        pid = _int_or_none(event.get("pid", ""))
        detail_parent_pid = _detail_value(detail, "Parent PID")
        parent_pid = _int_or_none(detail_parent_pid)
        parent_pid = parent_pid or pid

        process_path = image_path or command_line_executable(command_line)
        if not process_path:
            return

        item = {
            "process": process_path,
            "process_name": Path(process_path).name,
            "command_line": command_line,
            "count": 0,
            "first_seen": "",
            "last_seen": "",
        }

        if child_pid is not None:
            item["pid"] = child_pid
        if parent_pid is not None:
            item["parent_pid"] = parent_pid

        key_values = [
            normalize_path(process_path),
            normalize_command_line(command_line),
        ]

        if child_pid is not None:
            key_values.append(str(child_pid))

        processes_created = state["processes"]["created"]
        merge_item(
            processes_created,
            tuple(key_values),
            item,
            event,
        )
        return

    if operation in PROCESS_TERMINATED_OPERATIONS:
        detail = event.get("detail", "")
        pid = _int_or_none(event.get("pid", ""))
        exit_status = _detail_value(detail, "Exit Status")
        process_name = event.get("process_name", "")

        item = {
            "process_name": process_name,
            "exit_status": exit_status,
            "count": 0,
            "first_seen": "",
            "last_seen": "",
        }

        if pid is not None:
            item["pid"] = pid

        processes_terminated = state["processes"]["terminated"]
        key_values = (process_name.lower(), str(pid), exit_status)
        merge_item(
            processes_terminated,
            key_values,
            item,
            event,
        )
        return

    if operation in PROCESS_IMAGE_OPERATIONS:
        path = event.get("path", "")
        normalized_path = normalize_path(path)
        loaded_images = state["processes"]["loaded_images"]
        
        if path:
            loaded_images.setdefault(normalized_path, path)


def _record_filesystem_event(state: dict[str, Any], event: dict[str, str]) -> None:
    operation = event.get("operation", "")
    detail = event.get("detail", "")
    path = event.get("path", "")

    if not path:
        return

    if operation in FILESYSTEM_CREATED_OPERATIONS and _has_creation_disposition(detail):
        item = _with_event_metadata(file_item(path))
        
        files_created = state["filesystem"]["created"]
        normalized_path = normalize_path(path)

        merge_item(
            files_created, 
            (normalized_path,), 
            item, 
            event,
        )

        return

    action = _modification_action(operation)
    if action is not None:
        entity = filesystem_entity(state, path)
        entity["actions"].add(action)
        entity["last_path"] = path

        _update_seen_times(entity, event)

        if action == "content_modified":
            entity["write_count"] += 1
            length = _detail_number(detail, "Length")

            if length is not None:
                entity["bytes_written"] += length

        return

    if operation in FILESYSTEM_DELETED_OPERATIONS and _has_delete_disposition(detail):
        item = _with_event_metadata(file_item(path))

        files_deleted = state["filesystem"]["deleted"]
        normalized_path = normalize_path(path)

        merge_item(
            files_deleted, 
            (normalized_path,), 
            item, 
            event,
        )

        entity = filesystem_entity(state, path)
        entity["actions"].add("deleted")

        return

    if operation in FILESYSTEM_RENAMED_OPERATIONS:
        destination = _rename_destination(detail)
        if not destination:
            return

        same_directory = directory(path).lower() == directory(destination).lower()
        item = {
            "from": path,
            "to": destination,
            "source_extension": extension(path),
            "destination_extension": extension(destination),
            "same_directory": same_directory,
            "count": 0,
            "first_seen": "",
            "last_seen": "",
        }

        files_renamed = state["filesystem"]["renamed"]
        source_key = normalize_path(path)
        destination_key = normalize_path(destination)

        merge_item(
            files_renamed,
            (source_key, destination_key),
            item,
            event,
        )

        entity = filesystem_entity(state, path)
        entity["actions"].add("renamed")
        entity["renamed_to"] = destination

        _update_seen_times(entity, event)


def _with_event_metadata(item: dict[str, Any]) -> dict[str, Any]:
    item.update(
        {
            "count": 0, 
            "first_seen": "", 
            "last_seen": "",
        }
    )
    return item


def _update_seen_times(entity: dict[str, Any], event: dict[str, str]) -> None:
    event_time = event.get("time_of_day", "")

    entity["first_seen"] = entity["first_seen"] or event_time
    entity["last_seen"] = event_time or entity["last_seen"]


def _record_registry_event(state: dict[str, Any], event: dict[str, str]) -> None:
    operation = event.get("operation", "")
    detail = event.get("detail", "")
    path = event.get("path", "")

    if not path:
        return

    if operation in REGISTRY_CREATED_OPERATIONS and _has_created_registry_key(detail):
        item = registry_item(path, operation)

        registries_created = state["registry"]["created"]
        normalized_path = normalize_path(path)

        merge_item(
            registries_created,
            (normalized_path, operation),
            item,
            event,
        )

        return

    if operation in REGISTRY_MODIFIED_OPERATIONS:
        value_type = _detail_value(detail, "Type")
        data = _detail_value(detail, "Data")

        item = registry_item(path, operation)
        item["value_type"] = value_type or None
        item["data"] = data or None

        length = _detail_number(detail, "Length")
        if length is not None:
            item["data_length"] = length

        registries_modified = state["registry"]["modified"]
        normalized_path = normalize_path(path)

        merge_item(
            registries_modified,
            (
                normalized_path, 
                operation, 
                value_type.lower(), 
                data.lower(),
            ),
            item,
            event,
        )
        return

    if operation in REGISTRY_DELETED_OPERATIONS:
        item = registry_item(path, operation)

        registries_deleted = state["registry"]["deleted"]
        normalized_path = normalize_path(path)

        merge_item(
            registries_deleted,
            (normalized_path, operation),
            item,
            event,
        )


def _record_network_event(state: dict[str, Any], event: dict[str, str]) -> None:
    operation = event.get("operation", "")
    protocol = _network_protocol(operation)

    if protocol is None:
        return

    path = event.get("path", "")
    endpoints = _parse_network_path(path)

    if endpoints is None:
        return

    item = network_item(protocol, endpoints)
    local_address = str(item["local_address"])
    local_port = item["local_port"]
    remote_address = str(item["remote_address"])
    remote_port = item["remote_port"]

    key = (
        protocol,
        local_address.lower(),
        local_port,
        remote_address.lower(),
        remote_port,
    )

    network_connections = state["network"]["connections"]

    existing = merge_item(
        network_connections, 
        key, 
        item, 
        event,
    )

    detail = event.get("detail", "")

    update_connection_counts(existing, operation, detail)
    update_info_local_address(state, existing)

    if remote_port == 53 or local_port == 53:
        dns = dns_item(protocol, item)
        protocol = dns["protocol"]
        server = str(dns["server"])
        port = dns["port"]

        dns_key = (protocol, server.lower(), port)
        network_dns = state["network"]["dns"]

        existing_dns = merge_item(
            network_dns, 
            dns_key, 
            dns, 
            event,
        )

        update_dns_counts(existing_dns, operation)


def _network_protocol(operation: str) -> str | None:
    if operation in TCP_OPERATIONS:
        return "tcp"
    if operation in UDP_OPERATIONS:
        return "udp"
    
    return None


def _modification_action(operation: str) -> str | None:
    if operation in CONTENT_MODIFICATION_OPERATIONS:
        return "content_modified"
    if operation in METADATA_MODIFICATION_OPERATIONS:
        return "metadata_modified"
    if operation in SECURITY_MODIFICATION_OPERATIONS:
        return "security_modified"
    if operation in TRUNCATION_OPERATIONS:
        return "file_truncated"
    if operation in ALLOCATION_MODIFICATION_OPERATIONS:
        return "allocation_modified"
    
    return None


def _process_child_pid(detail: str) -> int | None:
    return (
        _int_or_none(_detail_value(detail, "PID"))
        or _int_or_none(_detail_value(detail, "Process ID"))
    )


def _parse_network_path(path: str) -> dict[str, Any] | None:
    if " -> " in path:
        local, remote = path.split(" -> ", 1)
    elif "=>" in path:
        local, remote = path.split("=>", 1)
    else:
        return None

    local_endpoint = _parse_endpoint(local.strip())
    remote_endpoint = _parse_endpoint(remote.strip())

    if local_endpoint is None or remote_endpoint is None:
        return None

    return {
        "local_address": local_endpoint[0],
        "local_port": local_endpoint[1],
        "remote_address": remote_endpoint[0],
        "remote_port": remote_endpoint[1],
    }


def _parse_endpoint(value: str) -> tuple[str, int | str] | None:
    match = re.match(r"^(.*):([^:]+)$", value.strip())
    if not match:
        return None
    
    address = match.group(1)
    port = match.group(2)
    service_port = SERVICE_PORTS.get(port.lower(), _int_or_string(port))

    return address, service_port


def _rename_destination(detail: str) -> str:
    for key in ("FileName", "Name", "Destination"):
        value = _detail_value(detail, key)

        if value:
            return value
        
    return ""


def _has_creation_disposition(detail: str) -> bool:
    value = detail.lower()

    if "disposition:" not in value:
        return False
    if re.search(r"disposition:\s*(create|create new)\b", value):
        return True
    if re.search(r"disposition:\s*(openif|overwriteif)\b", value):
        return "created" in value or "new file" in value
    
    return False


def _has_delete_disposition(detail: str) -> bool:
    value = detail.lower()

    return (
        "delete: true" in value
        or "delete-on-close" in value
        or "delete disposition" in value
        or "set disposition" in value
    )


def _has_created_registry_key(detail: str) -> bool:
    value = detail.lower()

    return (
        "created new key" in value
        or "disposition: created" in value
        or "new key" in value
    )


def _detail_value(detail: str, key: str) -> str:
    pattern = re.compile(r"(?:^|,\s*){0}:\s*([^,]+)".format(re.escape(key)), re.IGNORECASE)
    match = pattern.search(detail)
    
    return match.group(1).strip() if match else ""


def _detail_number(detail: str, key: str) -> int | None:
    value = _detail_value(detail, key)
    if not value:
        return None
    
    digits = re.sub(r"\D", "", value)
    return int(digits) if digits else None


def _normalize_field_name(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)

    return value.strip("_")


def _int_or_none(value: Any) -> int | None:
    try:
        return int(str(value).strip())
    except Exception:
        return None


def _int_or_string(value: str) -> int | str:
    try:
        return int(str(value).strip())
    except Exception:
        return value


def _sample_process_names(sample: Path) -> set[str]:
    process_names = {sample.name.lower()}

    if sample.suffix.lower() != ".exe":
        process_names.add((sample.stem + ".exe").lower())
        process_names.add((sample.name + ".exe").lower())
        
    return process_names
