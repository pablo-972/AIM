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


SUCCESS_RESULTS = {"SUCCESS"}

PROCESS_CREATED_OPERATIONS = {"Process Create"}
PROCESS_TERMINATED_OPERATIONS = {"Process Exit"}
PROCESS_IMAGE_OPERATIONS = {"Load Image"}

FILESYSTEM_CREATED_OPERATIONS = {"CreateFile", "CreateDirectory"}
FILESYSTEM_MODIFIED_OPERATIONS = {
    "WriteFile",
    "SetEndOfFileInformationFile",
    "SetAllocationInformationFile",
    "SetBasicInformationFile",
    "SetSecurityFile",
    "SetEaFile",
    "SetInformationFile",
}
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
FILESYSTEM_IGNORED_MODIFICATION_OPERATIONS = {
    "ReadFile",
    "QueryInformationFile",
    "QueryOpen",
    "CloseFile",
    "Cleanup",
    "FlushBuffersFile",
    "LockFile",
    "UnlockFile",
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
    sample_process_names = _sample_process_names(sample)

    return parse_procmon_csv(csv_path, sample_process_names)


def parse_procmon_csv(path: Path, process_names: set[str]) -> dict[str, Any]:
    behavior = _empty_behavior()
    if not path.exists():
        return behavior

    _raise_csv_field_limit()
    indexes = _empty_indexes()

    with io.StringIO(_read_csv_text(path), newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            parsed = {}

            for key, value in row.items():
                if not key:
                    continue

                normalized_key = _normalize_field_name(key)
                parsed[normalized_key] = (value or "").strip()

            process_name = parsed.get("process_name", "").lower()
            if process_name not in process_names:
                continue

            _record_procmon_event(behavior, indexes, parsed)

    return behavior


def _empty_behavior() -> dict[str, Any]:
    return {
        "processes": {
            "created": [],
            "terminated": [],
            "loaded_images": [],
        },
        "filesystem": {
            "created": [],
            "modified": [],
            "deleted": [],
            "renamed": [],
        },
        "registry": {
            "created": [],
            "modified": [],
            "deleted": [],
        },
        "network": {
            "dns": [],
            "tcp": [],
            "udp": [],
        },
        "statistics": {},
    }


def _empty_indexes() -> dict[str, dict[tuple[Any, ...], dict[str, Any]]]:
    return {
        "processes.created": {},
        "processes.terminated": {},
        "processes.loaded_images": {},
        "filesystem.created": {},
        "filesystem.modified": {},
        "filesystem.deleted": {},
        "filesystem.renamed": {},
        "registry.created": {},
        "registry.modified": {},
        "registry.deleted": {},
        "network.dns": {},
        "network.tcp": {},
        "network.udp": {},
    }


def _record_procmon_event(
    behavior: dict[str, Any],
    indexes: dict[str, dict[tuple[Any, ...], dict[str, Any]]],
    event: dict[str, str],
) -> None:
    operation = event.get("operation", "")
    result = event.get("result", "")

    if operation:
        statistics = behavior["statistics"]
        statistics[operation] = statistics.get(operation, 0) + 1

    if not _is_success(result):
        return

    _classify_process_event(behavior, indexes, event)
    _classify_filesystem_event(behavior, indexes, event)
    _classify_registry_event(behavior, indexes, event)
    _classify_network_event(behavior, indexes, event)


def _classify_process_event(
    behavior: dict[str, Any],
    indexes: dict[str, dict[tuple[Any, ...], dict[str, Any]]],
    event: dict[str, str],
) -> None:
    operation = event.get("operation", "")

    if operation in PROCESS_CREATED_OPERATIONS:
        detail = event.get("detail", "")
        item = _base_event(event)

        process_detail = _process_create_detail(detail)
        item.update(process_detail)

        process_name = item.get("process_name")
        pid = item.get("pid")
        command_line = item.get("command_line")

        key = (process_name, pid, command_line)
        processes_created = behavior["processes"]["created"]
        processes_created_indexes = indexes["processes.created"]

        _add_aggregated(
            processes_created, 
            processes_created_indexes, 
            key, 
            item,
        )

        return

    if operation in PROCESS_TERMINATED_OPERATIONS:
        item = _base_event(event)
        detail = event.get("detail", "")

        exit_status = _detail_value(detail, "Exit Status")
        if exit_status:
            item["exit_status"] = exit_status
        
        process_name = item.get("process_name")
        pid = item.get("pid")
        exit_status = item.get("exit_status")

        key = (process_name, pid, exit_status)
        processes_terminated = behavior["processes"]["terminated"]
        processes_terminated_indexes = indexes["processes.terminated"]

        _add_aggregated(
            processes_terminated, 
            processes_terminated_indexes, 
            key, 
            item,
        )

        return

    if operation in PROCESS_IMAGE_OPERATIONS:
        item = _base_event(event)
        item["image_path"] = event.get("path", "")

        process_name = item.get("process_name")
        pid = item.get("pid")
        image_path = _normalize_path(item.get("image_path", ""))

        key = (process_name, pid, image_path)
        processes_loaded_images = behavior["processes"]["loaded_images"]
        processes_loaded_images_indexes = indexes["processes.loaded_images"]

        _add_aggregated(
            processes_loaded_images,
            processes_loaded_images_indexes,
            key,
            item,
        )


def _classify_filesystem_event(
    behavior: dict[str, Any],
    indexes: dict[str, dict[tuple[Any, ...], dict[str, Any]]],
    event: dict[str, str],
) -> None:
    operation = event.get("operation", "")
    if operation in FILESYSTEM_IGNORED_MODIFICATION_OPERATIONS:
        return
    
    detail = event.get("detail", "")
    has_creation_disponition = _has_creation_disposition(detail)

    if operation in FILESYSTEM_CREATED_OPERATIONS and has_creation_disponition:
        item = _path_event(event)
        item["object_type"] = _filesystem_object_type(event)

        key = _path_event_key(item)
        filesystem_created = behavior["filesystem"]["created"]
        filesystem_created_indexes = indexes["filesystem.created"]

        _add_aggregated(
            filesystem_created,
            filesystem_created_indexes, 
            key,
            item,
        )

        return

    if operation in FILESYSTEM_MODIFIED_OPERATIONS:
        item = _path_event(event)

        if operation == "WriteFile":
            item["modification_type"] = "content"
            item["write_count"] = 1

            detail = event.get("detail", "")
            length = _detail_number(detail, "Length")

            if length is not None:
                item["bytes_written"] = length
        else:
            item["modification_type"] = "metadata"

        key = _path_event_key(item)
        filesystem_modified = behavior["filesystem"]["modified"]
        filesystem_modified_indexes = indexes["filesystem.modified"]
        numeric_fields = ("write_count", "bytes_written")

        _add_aggregated(
            filesystem_modified,
            filesystem_modified_indexes,
            key,
            item,
            numeric_fields=numeric_fields,
        )

        return

    has_delete_disposition = _has_delete_disposition(detail)
    if operation in FILESYSTEM_DELETED_OPERATIONS and has_delete_disposition:
        item = _path_event(event)
        key = _path_event_key(item)
        filesystem_deleted = behavior["filesystem"]["deleted"]
        filesystem_deleted_indexes = indexes["filesystem.deleted"]

        _add_aggregated(
            filesystem_deleted, 
            filesystem_deleted_indexes, 
            key, 
            item,
        )

        return

    if operation in FILESYSTEM_RENAMED_OPERATIONS:
        item = _base_event(event)
        path = event.get("path", "")

        item["old_path"] = path
        item["new_path"] = _rename_destination(detail)

        if not item["new_path"]:
            return
        
        process_name = item.get("process_name")
        pid = item.get("pid")
        normalized_old_path =  _normalize_path(item.get("old_path", ""))
        normalized_new_path = _normalize_path(item.get("new_path", ""))

        key = (
            process_name,
            pid,
            normalized_old_path,
            normalized_new_path,
        )
        filesystem_renamed = behavior["filesystem"]["renamed"]
        filesystem_renamed_indexes = indexes["filesystem.renamed"]

        _add_aggregated(filesystem_renamed, filesystem_renamed_indexes, key, item)


def _classify_registry_event(
    behavior: dict[str, Any],
    indexes: dict[str, dict[tuple[Any, ...], dict[str, Any]]],
    event: dict[str, str],
) -> None:
    operation = event.get("operation", "")
    detail = event.get("detail", "")

    has_created_registry_key = has_created_registry_key(detail)
    if operation in REGISTRY_CREATED_OPERATIONS and has_created_registry_key:
        item = _registry_event(event)
        key = _registry_event_key(item)
        registry_created = behavior["registry"]["created"]
        registry_created_indexes = indexes["registry.created"]

        _add_aggregated(
            registry_created, 
            registry_created_indexes, 
            key, 
            item,
        )

        return

    if operation in REGISTRY_MODIFIED_OPERATIONS:
        item = _registry_event(event)
        _add_registry_detail(item, detail)

        key = _registry_event_key(item)
        registry_modified = behavior["registry"]["modified"]
        registry_modified_indexes = indexes["registry.modified"]

        _add_aggregated(
            registry_modified, 
            registry_modified_indexes, 
            key, 
            item,
        )

        return

    if operation in REGISTRY_DELETED_OPERATIONS:
        item = _registry_event(event)
        key = _registry_event_key(item)
        registry_deleted = behavior["registry"]["deleted"]
        registry_deleted_indexes = indexes["registry.deleted"]

        _add_aggregated(
            registry_deleted, 
            registry_deleted_indexes, 
            key, 
            item,
        )

        return


def _classify_network_event(
    behavior: dict[str, Any],
    indexes: dict[str, dict[tuple[Any, ...], dict[str, Any]]],
    event: dict[str, str],
) -> None:
    operation = event.get("operation", "")

    if operation in TCP_OPERATIONS:
        item = _network_event(event, "tcp")
        if not item:
            return
        
        key = _network_event_key(item)
        _add_network_counters(item, event)

        network_tcp = behavior["network"]["tcp"]
        network_tcp_indexes = indexes["network.tcp"]
        numeric_fields = ("send_count", "receive_count", "bytes_sent", "bytes_received")

        _add_aggregated(
            network_tcp,
            network_tcp_indexes,
            key,
            item,
            numeric_fields=numeric_fields,
        )

        if _is_dns_transport(item):
            dns_item = _dns_event(item, "tcp")
            dns_key = _network_event_key(dns_item)

            network_dns = behavior["network"]["dns"]
            network_dns_indexes = indexes["network.dns"]

            _add_aggregated(
                network_dns, 
                network_dns_indexes,
                dns_key, 
                dns_item,
            )

        return

    if operation in UDP_OPERATIONS:
        item = _network_event(event, "udp")
        if not item:
            return
        
        key = _network_event_key(item)
        _add_network_counters(item, event)

        network_udp = behavior["network"]["udp"]
        network_udp_indexes = indexes["network.udp"]
        numeric_fields = ("send_count", "receive_count", "bytes_sent", "bytes_received")

        _add_aggregated(
            network_udp,
            network_udp_indexes,
            key,
            item,
            numeric_fields=numeric_fields,
        )

        if _is_dns_transport(item):
            dns_item = _dns_event(item, "udp")
            dns_key = _network_event_key(dns_item)

            network_dns = behavior["network"]["dns"]
            network_dns_indexes = indexes["network.dns"]

            _add_aggregated(
                network_dns, 
                network_dns_indexes,
                dns_key, 
                dns_item,
            )

        return


def _add_aggregated(
    collection: list[dict[str, Any]],
    index: dict[tuple[Any, ...], dict[str, Any]],
    key: tuple[Any, ...],
    item: dict[str, Any],
    numeric_fields: tuple[str, ...] = (),
) -> None:
    timestamp = item.pop("time", "")
    existing = index.get(key)

    if existing is None:
        item["count"] = item.get("count", 1)
        item["first_seen"] = timestamp
        item["last_seen"] = timestamp

        index[key] = item
        collection.append(item)

        return

    existing["count"] = existing.get("count", 1) + item.get("count", 1)

    if timestamp:
        if not existing.get("first_seen"):
            existing["first_seen"] = timestamp

        existing["last_seen"] = timestamp

    for field in numeric_fields:
        if field in item:
            existing[field] = existing.get(field, 0) + item[field]


def _base_event(event: dict[str, str]) -> dict[str, Any]:
    process_name = event.get("process_name", "")
    pid = _int_or_string(event.get("pid", ""))
    operation = event.get("operation", "")
    time = event.get("time_of_day", "")

    return {
        "process_name": process_name,
        "pid": pid,
        "operation": operation,
        "time": time,
    }


def _path_event(event: dict[str, str]) -> dict[str, Any]:
    item = _base_event(event)
    item["path"] = event.get("path", "")

    return item


def _registry_event(event: dict[str, str]) -> dict[str, Any]:
    item = _base_event(event)
    item["path"] = event.get("path", "")

    return item


def _path_event_key(item: dict[str, Any]) -> tuple[Any, ...]:
    process_name = item.get("process_name", "")
    pid = item.get("pid", "")
    operation = item.get("operation", "")
    normalized_path = _normalize_path(item.get("path", ""))

    return (
        process_name,
        pid,
        operation,
        normalized_path,
    )


def _registry_event_key(item: dict[str, Any]) -> tuple[Any, ...]:
    process_name = item.get("process_name", "")
    pid = item.get("pid", "")
    operation = item.get("operation", "")
    normalized_path = _normalize_path(item.get("path", ""))

    return (
        process_name,
        pid,
        operation,
        normalized_path,
    )


def _sample_process_names(sample: Path) -> set[str]:
    process_names = {sample.name.lower()}

    if sample.suffix.lower() == ".exe":
        process_names.add(sample.name.lower())
    else:
        process_names.add((sample.stem + ".exe").lower())
        process_names.add((sample.name + ".exe").lower())

    return process_names


def _is_success(result: str) -> bool:
    return result.upper() in SUCCESS_RESULTS


def _has_creation_disposition(detail: str) -> bool:
    detail = detail.lower()

    if "disposition:" not in detail:
        return False
    
    if re.search(r"disposition:\s*(create|create new)\b", detail):
        return True
    
    if re.search(r"disposition:\s*(openif|overwriteif)\b", detail):
        return "created" in detail or "new file" in detail
    
    return False


def _has_delete_disposition(detail: str) -> bool:
    detail = detail.lower()

    return (
        "delete: true" in detail
        or "delete-on-close" in detail
        or "delete disposition" in detail
        or "set disposition" in detail
    )


def _has_created_registry_key(detail: str) -> bool:
    detail = detail.lower()

    return (
        "created new key" in detail 
        or "disposition: created" in detail 
        or "new key" in detail
    )


def _filesystem_object_type(event: dict[str, str]) -> str:
    detail = event.get("detail", "").lower()
    path = event.get("path", "")

    if "directory" in detail or path.endswith("\\"):
        return "directory"
    
    if "." in Path(path).name:
        return "file"
    
    return "unknown"


def _process_create_detail(detail: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    parent_pid = _detail_value(detail, "Parent PID")
    command_line = _detail_value(detail, "Command line")
    image_path = _detail_value(detail, "Image Path")
    architecture = _detail_value(detail, "Architecture")

    if parent_pid:
        parsed["parent_pid"] = _int_or_string(parent_pid)
    if command_line:
        parsed["command_line"] = command_line
    if image_path:
        parsed["image_path"] = image_path
    if architecture:
        parsed["architecture"] = architecture

    return parsed


def _add_registry_detail(item: dict[str, Any], detail: str) -> None:
    value_type = _detail_value(detail, "Type")
    data = _detail_value(detail, "Data")
    length = _detail_number(detail, "Length")

    if value_type:
        item["value_type"] = value_type
    if data:
        item["data"] = data
    if length is not None:
        item["data_length"] = length


def _network_event(event: dict[str, str], protocol: str) -> dict[str, Any] | None:
    path = event.get("path", "")
    endpoints = _parse_network_path(path)

    if endpoints is None:
        return None

    item = _base_event(event)
    item["protocol"] = protocol
    item.update(endpoints)

    operation = event.get("operation")
    tcp_connection = ("TCP Connect", "TCP Reconnect", "TCP Accept")

    if operation in tcp_connection:
        item["connected"] = True

    return item


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
    value = value.strip()
    match = re.match(r"^(.*):([^:]+)$", value)

    if not match:
        return None

    address = match.group(1)
    port = match.group(2)
    normalized_port = SERVICE_PORTS.get(port.lower(), _int_or_string(port))

    return address, normalized_port


def _network_event_key(item: dict[str, Any]) -> tuple[Any, ...]:
    proccess_name = item.get("process_name")
    pid = item.get("pid")
    protocol = item.get("protocol")
    local_address = item.get("local_address")
    local_port = item.get("local_port")
    remote_address = item.get("remote_address")
    remote_port = item.get("remote_port")

    return (
        proccess_name,
        pid,
        protocol,
        local_address,
        local_port,
        remote_address,
        remote_port,
    )


def _add_network_counters(item: dict[str, Any], event: dict[str, str]) -> None:
    operation = event.get("operation", "")
    detail = event.get("detail", "")
    length = _detail_number(detail, "Length")

    if operation.endswith(" Send"):
        item["send_count"] = 1

        if length is not None:
            item["bytes_sent"] = length

    elif operation.endswith(" Receive"):
        item["receive_count"] = 1
        
        if length is not None:
            item["bytes_received"] = length


def _is_dns_transport(item: dict[str, Any]) -> bool:
    remote_port = item.get("remote_port")
    local_port = item.get("local_port")

    return remote_port == 53 or local_port == 53


def _dns_event(item: dict[str, Any], protocol: str) -> dict[str, Any]:
    server = item.get("remote_address")
    port = item.get("remote_port")

    if port != 53:
        server = item.get("local_address")
        port = item.get("local_port")

    process_name = item.get("process_name", "")
    pid = item.get("pid", "")
    operation = item.get("operation", "")
    time = item.get("time", "")

    return {
        "process_name": process_name,
        "pid": pid,
        "server": server,
        "port": port,
        "protocol": protocol,
        "domain": None,
        "operation": operation,
        "time": time,
    }


def _rename_destination(detail: str) -> str:
    destinations = ("FileName", "Name", "Destination")

    for key in destinations:
        value = _detail_value(detail, key)

        if value:
            return value
        
    return ""


def _detail_value(detail: str, key: str) -> str:
    pattern = re.compile(r"(?:^|,\s*){0}:\s*([^,]+)".format(re.escape(key)), re.IGNORECASE)
    match = pattern.search(detail)

    if not match:
        return ""
    
    return match.group(1).strip()


def _detail_number(detail: str, key: str) -> int | None:
    value = _detail_value(detail, key)
    if not value:
        return None
    
    digits = re.sub(r"\D", "", value)
    if not digits:
        return None
    
    return int(digits)


def _normalize_path(path: str) -> str:
    return path.strip().replace("/", "\\").lower()


def _int_or_string(value: str) -> int | str:
    try:
        return int(str(value).strip())
    except Exception:
        return value


def _normalize_field_name(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)

    return value.strip("_")


def _read_csv_text(path: Path) -> str:
    raw = path.read_bytes()
    encoders = ("utf-16", "utf-8-sig", "latin-1")

    for encoding in encoders:
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
