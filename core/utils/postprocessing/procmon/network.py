import re
from typing import Any, Iterable

from core.utils.postprocessing.procmon.common import (
    MAX_GROUPS,
    MAX_NETWORK_ITEMS,
    collection,
    detail_number,
    generic_item_key,
    normalize_row_key,
)


NETWORK_COUNT_FIELDS = (
    "connect_count",
    "reconnect_count",
    "accept_count",
    "send_count",
    "receive_count",
    "disconnect_count",
)


def network_result(state: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    network_state = state["network"]

    connection_items = list(network_state["connections"].values())
    dns_items = list(network_state["dns"].values())

    finalized_connections = []
    for item in connection_items:
        finalized_connections.append(_finalize_connection_item(item))

    finalized_dns = []
    for item in dns_items:
        finalized_dns.append(_finalize_dns_item(item))

    network = {
        "connections": collection(
            finalized_connections,
            MAX_NETWORK_ITEMS,
            _network_groups(connection_items),
            _network_item_key,
        ),
        "dns": collection(
            finalized_dns,
            MAX_NETWORK_ITEMS,
            _dns_groups(dns_items),
            generic_item_key,
        ),
    }

    return network, _network_operation_totals(connection_items)


def network_item(protocol: str, endpoints: dict[str, Any]) -> dict[str, Any]:
    local_address = endpoints["local_address"]
    local_port = endpoints["local_port"]
    remote_address = endpoints["remote_address"]
    remote_port = endpoints["remote_port"]

    return {
        "protocol": protocol,
        "local_address": local_address,
        "local_port": local_port,
        "remote_address": remote_address,
        "remote_port": remote_port,
        "connect_count": 0,
        "reconnect_count": 0,
        "accept_count": 0,
        "send_count": 0,
        "receive_count": 0,
        "disconnect_count": 0,
        "bytes_sent": 0,
        "bytes_received": 0,
        "count": 0,
        "first_seen": "",
        "last_seen": "",
    }


def dns_item(protocol: str, connection: dict[str, Any]) -> dict[str, Any]:
    server = connection["remote_address"]
    port = connection["remote_port"]
    
    if port != 53:
        server = connection["local_address"]
        port = connection["local_port"]

    return {
        "protocol": protocol,
        "server": server,
        "port": port,
        "domain": None,
        "send_count": 0,
        "receive_count": 0,
        "count": 0,
        "first_seen": "",
        "last_seen": "",
    }


def update_connection_counts(item: dict[str, Any], operation: str, detail: str) -> None:
    length = detail_number(detail, "Length") or 0

    if operation == "TCP Connect":
        item["connect_count"] += 1
        item["connected"] = True
    elif operation == "TCP Reconnect":
        item["reconnect_count"] += 1
    elif operation == "TCP Accept":
        item["accept_count"] += 1
        item["connected"] = True
    elif operation in {"TCP Send", "UDP Send"}:
        item["send_count"] += 1
        item["bytes_sent"] += length
    elif operation in {"TCP Receive", "UDP Receive"}:
        item["receive_count"] += 1
        item["bytes_received"] += length
    elif operation == "TCP Disconnect":
        item["disconnect_count"] += 1
        item["connected"] = False


def update_dns_counts(item: dict[str, Any], operation: str) -> None:
    if operation in {"TCP Send", "UDP Send"}:
        item["send_count"] += 1
    elif operation in {"TCP Receive", "UDP Receive"}:
        item["receive_count"] += 1


def update_info_local_address(state: dict[str, Any], connection: dict[str, Any]) -> None:
    info = state["info"]
    local_address = connection.get("local_address")

    if not info["local_address"] and local_address:
        info["local_address"] = local_address


def _finalize_connection_item(item: dict[str, Any]) -> dict[str, Any]:
    finalized = {}
    for key, value in item.items():
        if key != "count":
            finalized[key] = value

    if finalized.get("connected") is None:
        finalized.pop("connected", None)

    if not finalized.get("bytes_sent"):
        finalized.pop("bytes_sent", None)

    if not finalized.get("bytes_received"):
        finalized.pop("bytes_received", None)

    return finalized


def _finalize_dns_item(item: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for key, value in item.items():
        if key != "count":
            result[key] = value

    return result


def _network_groups(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    protocol: dict[Any, dict[str, Any]] = {}
    remote_port: dict[Any, dict[str, Any]] = {}
    remote_address: dict[Any, dict[str, Any]] = {}
    remote_address_type: dict[Any, dict[str, Any]] = {}
    remote_endpoint: dict[tuple[Any, ...], dict[str, Any]] = {}

    for item in items:
        item_protocol = item.get("protocol")
        item_remote_port = item.get("remote_port")
        item_remote_address = item.get("remote_address", "")

        _add_network_group_metrics(protocol, item_protocol or "", item)
        _add_network_group_metrics(remote_port, item_remote_port, item)
        _add_network_group_metrics(remote_address, item_remote_address, item)
        _add_network_group_metrics(
            remote_address_type,
            _address_type(str(item_remote_address)),
            item,
        )

        endpoint_key = (
            item_protocol,
            str(item_remote_address).lower(),
            item_remote_port,
        )

        endpoint = remote_endpoint.get(endpoint_key)

        if endpoint is None:
            endpoint = {
                "type": "remote_endpoint",
                "protocol": item_protocol,
                "remote_address": item_remote_address,
                "remote_port": item_remote_port,
                "unique_connections": 0,
                "connect_count": 0,
                "reconnect_count": 0,
                "accept_count": 0,
                "send_count": 0,
                "receive_count": 0,
                "disconnect_count": 0,
                "bytes_sent": 0,
                "bytes_received": 0,
            }

            remote_endpoint[endpoint_key] = endpoint

        _add_network_operation_metrics(endpoint, item)

    groups = [
        *_network_metric_groups("remote_endpoint", remote_endpoint),
        *_network_metric_groups("protocol", protocol),
        *_network_metric_groups("remote_port", remote_port),
        *_network_metric_groups("remote_address", remote_address),
        *_network_metric_groups("remote_address_type", remote_address_type),
    ]

    return groups[:MAX_GROUPS]


def _dns_groups(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    protocol_groups = {}
    server_groups = {}
    port_groups = {}

    for item in items:
        protocol = item.get("protocol", "")
        server = item.get("server", "")
        port = item.get("port")

        _add_dns_group_metrics(protocol_groups, protocol, item)
        _add_dns_group_metrics(server_groups, server, item)
        _add_dns_group_metrics(port_groups, port, item)

    groups = [
        *_dns_metric_groups("protocol", protocol_groups),
        *_dns_metric_groups("server", server_groups),
        *_dns_metric_groups("port", port_groups),
    ]

    return groups[:MAX_GROUPS]


def _add_dns_group_metrics(
    groups: dict[Any, dict[str, Any]],
    value: Any,
    item: dict[str, Any],
) -> None:
    if value in ("", None):
        return

    group = groups.get(value)
    if group is None:
        group = {
            "value": value,
            "unique_transports": 0,
            "operation_count": 0,
        }
        groups[value] = group

    send_count = int(item.get("send_count", 0))
    receive_count = int(item.get("receive_count", 0))

    group["unique_transports"] += 1
    group["operation_count"] += send_count + receive_count


def _dns_metric_groups(
    group_type: str,
    groups: dict[Any, dict[str, Any]],
) -> list[dict[str, Any]]:
    items = []

    for group in groups.values():
        items.append(
            {
                "type": group_type,
                **group,
            }
        )

    return sorted(
        items,
        key=lambda item: (
            -int(item.get("operation_count", 0)),
            -int(item.get("unique_transports", 0)),
            str(item.get("value", "")),
        ),
    )


def _add_network_group_metrics(
    groups: dict[Any, dict[str, Any]],
    value: Any,
    item: dict[str, Any],
) -> None:
    if value in ("", None):
        return

    group = groups.get(value)
    if group is None:
        group = {
            "value": value,
            "unique_connections": 0,
            "operation_count": 0,
        }
        groups[value] = group

    group["unique_connections"] += 1
    group["operation_count"] += _network_operation_count(item)


def _add_network_operation_metrics(
    target: dict[str, Any],
    item: dict[str, Any],
) -> None:
    target["unique_connections"] += 1
    for key in NETWORK_COUNT_FIELDS:
        target[key] += int(item.get(key, 0))

    target["bytes_sent"] += int(item.get("bytes_sent", 0))
    target["bytes_received"] += int(item.get("bytes_received", 0))


def _network_metric_groups(
    group_type: str,
    groups: dict[Any, dict[str, Any]],
) -> list[dict[str, Any]]:
    values = []
    for group in groups.values():
        item = {
            "type": group_type,
            **group,
        }

        if group_type == "remote_endpoint":
            item.pop("value", None)

            if not item.get("bytes_sent"):
                item.pop("bytes_sent", None)

            if not item.get("bytes_received"):
                item.pop("bytes_received", None)

        values.append(item)

    return sorted(
        values,
        key=lambda item: (
            -int(item.get("operation_count", _network_operation_count(item))),
            -int(item.get("unique_connections", 0)),
            str(item.get("value", item.get("remote_address", ""))),
            str(item.get("remote_port", "")),
        ),
    )


def _network_operation_totals(
    items: Iterable[dict[str, Any]],
) -> dict[str, int]:
    totals = {
        "connect": 0,
        "reconnect": 0,
        "accept": 0,
        "send": 0,
        "receive": 0,
        "disconnect": 0,
    }

    for item in items:
        connect_count = int(item.get("connect_count", 0))
        reconnect_count = int(item.get("reconnect_count", 0))
        accept_count = int(item.get("accept_count", 0))
        send_count = int(item.get("send_count", 0))
        receive_count = int(item.get("receive_count", 0))
        disconnect_count = int(item.get("disconnect_count", 0))

        totals["connect"] += connect_count
        totals["reconnect"] += reconnect_count
        totals["accept"] += accept_count
        totals["send"] += send_count
        totals["receive"] += receive_count
        totals["disconnect"] += disconnect_count

    return totals


def _network_operation_count(item: dict[str, Any]) -> int:
    total = 0
    for key in NETWORK_COUNT_FIELDS:
        total += int(item.get(key, 0))

    return total


def _network_item_key(item: dict[str, Any]) -> str:
    keys = (
        "protocol",
        "local_address",
        "local_port",
        "remote_address",
        "remote_port",
    )

    values = []
    for key in keys:
        values.append(normalize_row_key(item.get(key)))

    return "|".join(values)


def _address_type(value: str) -> str:
    if re.match(r"^\d{1,3}(?:\.\d{1,3}){3}$", value):
        return "ip"
    
    if value.startswith(("http://", "https://")) or "/" in value:
        return "url_like"
    
    if value:
        return "hostname"
    
    return "unknown"
