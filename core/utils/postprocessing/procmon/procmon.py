from typing import Any

from core.utils.postprocessing.procmon.filesystem import filesystem_result
from core.utils.postprocessing.procmon.network import network_result
from core.utils.postprocessing.procmon.process import process_result
from core.utils.postprocessing.procmon.registry import registry_result


def finalize_procmon_state(state: dict[str, Any]) -> dict[str, Any]:
    processes = process_result(state)
    filesystem = filesystem_result(state)
    registry = registry_result(state)
    network, network_operations = network_result(state)

    process_created_total = processes["created"]["total"]
    process_terminated_total = processes["terminated"]["total"]
    images_loaded_total = processes["loaded_images"]["total"]

    files_created_total = filesystem["created"]["total"]
    files_modified_total = filesystem["modified"]["total"]
    files_deleted_total = filesystem["deleted"]["total"]
    files_renamed_total = filesystem["renamed"]["total"]

    registry_created_total = registry["created"]["total"]
    registry_modified_total = registry["modified"]["total"]
    registry_deleted_total = registry["deleted"]["total"]

    network_connections_total = network["connections"]["total"]
    dns_transports_total = network["dns"]["total"]

    overview = {
        "processes_created": process_created_total,
        "processes_terminated": process_terminated_total,
        "images_loaded": images_loaded_total,
        "files_created": files_created_total,
        "files_modified": files_modified_total,
        "files_deleted": files_deleted_total,
        "files_renamed": files_renamed_total,
        "registry_created": registry_created_total,
        "registry_modified": registry_modified_total,
        "registry_deleted": registry_deleted_total,
        "network_connections": network_connections_total,
        "dns_transports": dns_transports_total,
        "network_operations": network_operations,
    }

    operation_statistics = dict(
        sorted(state["operation_statistics"].items())
    )

    return {
        "info": state["info"],
        "overview": overview,
        "processes": processes,
        "filesystem": filesystem,
        "registry": registry,
        "network": network,
        "operation_statistics": operation_statistics,
    }
