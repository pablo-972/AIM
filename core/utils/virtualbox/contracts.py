from typing import Any, Literal, TypedDict, cast, get_args


VMAction = Literal[
    "start",
    "stop",
    "restore_snapshot",
    "configure_shared_folder",
]
VMOperationStatus = Literal[
    "completed",
    "already_running",
    "already_stopped",
    "already_configured",
]


class VMOperationResult(TypedDict):
    action: VMAction
    vm: str
    status: VMOperationStatus
    changed: bool
    details: dict[str, Any]


class RunningVMsResult(TypedDict):
    running_vms: list[str]


def operation_result(
    action: VMAction,
    vm: str,
    status: VMOperationStatus,
    changed: bool,
    details: dict[str, Any] | None = None,
) -> VMOperationResult:
    return {
        "action": action,
        "vm": vm,
        "status": status,
        "changed": changed,
        "details": details or {},
    }


def validate_operation_result(data: dict[str, Any]) -> VMOperationResult:
    if data.get("action") not in get_args(VMAction):
        raise ValueError("VirtualBox response has an invalid action")
    if not isinstance(data.get("vm"), str):
        raise ValueError("VirtualBox response has an invalid VM name")
    if data.get("status") not in get_args(VMOperationStatus):
        raise ValueError("VirtualBox response has an invalid status")
    if not isinstance(data.get("changed"), bool):
        raise ValueError("VirtualBox response has an invalid changed flag")
    if not isinstance(data.get("details"), dict):
        raise ValueError("VirtualBox response has invalid details")

    return cast(VMOperationResult, data)


def validate_running_vms_result(data: dict[str, Any]) -> RunningVMsResult:
    running_vms = data.get("running_vms")

    if not isinstance(running_vms, list):
        raise ValueError(f"{running_vms} must be a list")
    
    for vm_name in running_vms:
        if not isinstance(vm_name, str):
            raise ValueError(f"{vm_name} must contain only strings")

    return cast(RunningVMsResult, data)
