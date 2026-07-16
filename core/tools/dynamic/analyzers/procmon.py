import csv
import io
import re
from typing import Any
from pathlib import Path

from core.utils.io.files import read_csv_text, raise_csv_field_limit

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

    raise_csv_field_limit()
    indexes = _empty_indexes()

    with io.StringIO(read_csv_text(path), newline="") as file:
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

    _update_statistics(behavior)
    return behavior


def _empty_behavior() -> dict[str, Any]:
    return {
        "info": {},
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
            "tcp": {
                "urls": [],
                "ips": [],
                "domains": [],
            },
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
        "network.tcp.urls": {},
        "network.tcp.ips": {},
        "network.tcp.domains": {},
        "network.udp": {},
    }


def _record_procmon_event(
    behavior: dict[str, Any],
    indexes: dict[str, dict[tuple[Any, ...], dict[str, Any]]],
    event: dict[str, str],
) -> None:
    result = event.get("result", "")

    if not _is_success(result):
        return

    _update_info(behavior, event)
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
        process_detail = _process_create_detail(detail)
        item = _process_created_path(event, process_detail)

        if not item:
            return

        key = (_normalize_path(item),)
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
        detail = event.get("detail", "")

        item = {}
        exit_status = _detail_value(detail, "Exit Status")
        if exit_status:
            item["exit_status"] = exit_status
        
        process_name = event.get("process_name", "")
        pid = event.get("pid", "")
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
        item = event.get("path", "")
        if not item:
            return

        key = (_normalize_path(item),)
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
    has_disponition = _has_creation_disposition(detail)

    if operation in FILESYSTEM_CREATED_OPERATIONS and has_disponition:
        item = event.get("path", "")
        if not item:
            return

        key = (_normalize_path(item),)
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
        if not item["path"]:
            return

        if operation == "WriteFile":
            item["modification_type"] = "content"
        else:
            item["modification_type"] = "metadata"

        key = (
            _normalize_path(item.get("path", "")),
            item.get("modification_type", ""),
        )
        filesystem_modified = behavior["filesystem"]["modified"]
        filesystem_modified_indexes = indexes["filesystem.modified"]

        _add_aggregated(
            filesystem_modified,
            filesystem_modified_indexes,
            key,
            item,
        )

        return

    has_delete_disposition = _has_delete_disposition(detail)
    if operation in FILESYSTEM_DELETED_OPERATIONS and has_delete_disposition:
        item = event.get("path", "")
        if not item:
            return

        key = (_normalize_path(item),)
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
        path = event.get("path", "")
        item = {
            "from": path,
            "to": _rename_destination(detail),
        }

        if not item["to"]:
            return
        
        process_name = event.get("process_name", "")
        pid = event.get("pid", "")
        normalized_old_path =  _normalize_path(item.get("from", ""))
        normalized_new_path = _normalize_path(item.get("to", ""))

        key = (
            process_name,
            pid,
            normalized_old_path,
            normalized_new_path,
        )
        filesystem_renamed = behavior["filesystem"]["renamed"]
        filesystem_renamed_indexes = indexes["filesystem.renamed"]

        _add_aggregated(
            filesystem_renamed, 
            filesystem_renamed_indexes, 
            key, 
            item,
        )


def _classify_registry_event(
    behavior: dict[str, Any],
    indexes: dict[str, dict[tuple[Any, ...], dict[str, Any]]],
    event: dict[str, str],
) -> None:
    operation = event.get("operation", "")
    detail = event.get("detail", "")

    created_registry_key = _has_created_registry_key(detail)
    if operation in REGISTRY_CREATED_OPERATIONS and created_registry_key:
        item = _path_event(event)
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
        item = _path_event(event)
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
        item = event.get("path", "")
        if not item:
            return

        key = (_normalize_path(item),)
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

        _update_network_info(behavior, item)

        _add_tcp_connection(behavior, indexes, item)

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

        _update_network_info(behavior, item)
        key = _network_event_key(item)

        network_udp = behavior["network"]["udp"]
        network_udp_indexes = indexes["network.udp"]

        _add_aggregated(
            network_udp,
            network_udp_indexes,
            key,
            _connection_endpoint(item),
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
    collection: list[Any],
    index: dict[tuple[Any, ...], Any],
    key: tuple[Any, ...],
    item: Any,
) -> None:
    existing = index.get(key)

    if existing is None:
        index[key] = item
        collection.append(item)

        return


def _update_info(
    behavior: dict[str, Any],
    event: dict[str, str],
) -> None:
    info = behavior["info"]

    if not info.get("process_name"):
        process_name = event.get("process_name")
        if process_name:
            info["process_name"] = process_name

    if not info.get("pid"):
        pid = event.get("pid")
        if pid:
            info["pid"] = _int_or_string(pid)


def _update_network_info(
    behavior: dict[str, Any],
    item: dict[str, Any],
) -> None:
    info = behavior["info"]

    if not info.get("local_address"):
        local_address = item.get("local_address")
        if local_address:
            info["local_address"] = local_address


def _update_statistics(behavior: dict[str, Any]) -> None:
    processes = behavior["processes"]
    filesystem = behavior["filesystem"]
    registry = behavior["registry"]
    network = behavior["network"]
    tcp = network["tcp"]

    behavior["statistics"] = {
        "processes_created": len(processes["created"]),
        "processes_terminated": len(processes["terminated"]),
        "images_loaded": len(processes["loaded_images"]),
        "filesystem_created": len(filesystem["created"]),
        "filesystem_modified": len(filesystem["modified"]),
        "filesystem_deleted": len(filesystem["deleted"]),
        "filesystem_renamed": len(filesystem["renamed"]),
        "registry_created": len(registry["created"]),
        "registry_modified": len(registry["modified"]),
        "registry_deleted": len(registry["deleted"]),
        "tcp_connections": (
            len(tcp["urls"]) 
            + len(tcp["ips"]) 
            + len(tcp["domains"])
        ),
        "tcp_urls": len(tcp["urls"]),
        "tcp_ips": len(tcp["ips"]),
        "tcp_domains": len(tcp["domains"]),
        "udp_connections": len(network["udp"]),
        "dns_connections": len(network["dns"]),
    }


def _base_event(event: dict[str, str]) -> dict[str, Any]:
    operation = event.get("operation", "")

    return {
        "operation": operation,
    }


def _path_event(event: dict[str, str]) -> dict[str, Any]:
    path = event.get("path", "")

    return {
        "path": path
    }


def _registry_event_key(item: dict[str, Any]) -> tuple[Any, ...]:
    operation = item.get("operation", "")
    path = item.get("path", "")
    normalized_path = _normalize_path(path)

    return (
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


def _process_created_path(
    event: dict[str, str],
    process_detail: dict[str, Any],
) -> str:
    image_path = process_detail.get("image_path")
    if image_path:
        return str(image_path)

    event_path = event.get("path")
    if event_path:
        return event_path

    command_line = process_detail.get("command_line")
    if isinstance(command_line, str):
        return _command_line_executable(command_line)

    return ""


def _command_line_executable(command_line: str) -> str:
    command_line = command_line.strip()
    if not command_line:
        return ""

    if command_line.startswith('"'):
        end = command_line.find('"', 1)
        if end > 1:
            return command_line[1:end]

    return command_line.split(" ", 1)[0]


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
    protocol = item.get("protocol")
    local_address = item.get("local_address")
    local_port = item.get("local_port")
    remote_address = item.get("remote_address")
    remote_port = item.get("remote_port")

    return (
        protocol,
        local_address,
        local_port,
        remote_address,
        remote_port,
    )


def _add_tcp_connection(
    behavior: dict[str, Any],
    indexes: dict[str, dict[tuple[Any, ...], Any]],
    item: dict[str, Any],
) -> None:
    endpoint = _connection_endpoint(item)
    if not endpoint:
        return

    category = _tcp_connection_category(item)
    collection = behavior["network"]["tcp"][category]
    index = indexes[f"network.tcp.{category}"]

    _add_aggregated(
        collection, 
        index, 
        (endpoint.lower(),), 
        endpoint,
    )


def _connection_endpoint(item: dict[str, Any]) -> str:
    remote_address = str(item.get("remote_address") or "")

    return _format_endpoint(
        remote_address,
        item.get("remote_port"),
    )


def _tcp_connection_category(item: dict[str, Any]) -> str:
    remote_address = str(item.get("remote_address") or "")

    if _is_ip_address(remote_address):
        return "ips"

    is_http = remote_address.lower().startswith(("http://", "https://"))
                                                
    if "/" in remote_address or is_http:
        return "urls"

    return "domains"


def _format_endpoint(address: Any, port: Any) -> str:
    if port in ("", None):
        return str(address or "")

    return f"{address}:{port}"


def _is_ip_address(value: str) -> bool:
    return bool(re.match(r"^\d{1,3}(?:\.\d{1,3}){3}$", value))


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

    operation = item.get("operation", "")

    return {
        "server": server,
        "port": port,
        "protocol": protocol,
        "domain": None,
        "operation": operation,
    }


def _rename_destination(detail: str) -> str:
    destinations = ("FileName", "Name", "Destination")

    for key in destinations:
        value = _detail_value(detail, key)

        if value:
            return value
        
    return ""


def _detail_value(detail: str, key: str) -> str:
    pattern = re.compile(
        r"(?:^|,\s*){0}:\s*([^,]+)".format(re.escape(key)), 
        re.IGNORECASE)
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
