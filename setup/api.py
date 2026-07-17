import uvicorn
from fastapi import FastAPI

from config import (
    DYNAMIC_ARTIFACTS_PATH,
    DYNAMIC_EXECUTION_PATH,
)
from setup.manager import VirtualBoxManager
from core.utils.virtualbox.contracts import (
    RunningVMsResult,
    VMOperationResult,
)


API_HOST = "0.0.0.0"
API_PORT = 8090


app = FastAPI(title="AIM VirtualBox Host API")
vbox = VirtualBoxManager(
    shared_paths={
        "execution": DYNAMIC_EXECUTION_PATH,
        "artifacts": DYNAMIC_ARTIFACTS_PATH,
    },
)


@app.get("/health")
def health() -> dict[str, object]:
    result = vbox.health()

    return result


@app.get("/vms/running")
def running_vms() -> RunningVMsResult:
    result = vbox.running_vms()

    return result


@app.post("/vms/{vm_name}/start")
def start_vm(vm_name: str) -> VMOperationResult:
    result = vbox.start_vm(vm_name)

    return result


@app.post("/vms/{vm_name}/poweroff")
def poweroff_vm(vm_name: str) -> VMOperationResult:
    result = vbox.poweroff_vm(vm_name)

    return result


@app.post("/vms/{vm_name}/snapshots/{snapshot_name}/restore")
def restore_snapshot(
    vm_name: str,
    snapshot_name: str,
) -> VMOperationResult:
    result = vbox.restore_snapshot(vm_name, snapshot_name)

    return result


@app.post("/vms/{vm_name}/shared-folders/{shared_folder}")
def configure_shared_folder(
    vm_name: str,
    shared_folder: str,
    readonly: bool = False,
    mount_point: str | None = None,
) -> VMOperationResult:
    result = vbox.configure_shared_folder(
        vm_name=vm_name,
        shared_folder=shared_folder,
        readonly=readonly,
        mount_point=mount_point,
    )

    return result


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT,
    )
