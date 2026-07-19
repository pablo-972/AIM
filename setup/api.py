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
    return vbox.health()


@app.get("/vms/running")
def running_vms() -> RunningVMsResult:
    return vbox.running_vms()


@app.post("/vms/{vm_name}/start")
def start_vm(vm_name: str) -> VMOperationResult:
    return vbox.start_vm(vm_name)


@app.post("/vms/{vm_name}/poweroff")
def poweroff_vm(vm_name: str) -> VMOperationResult:
    return vbox.poweroff_vm(vm_name)


@app.post("/vms/{vm_name}/snapshots/{snapshot_name}/restore")
def restore_snapshot(vm_name: str, snapshot_name: str) -> VMOperationResult:
    return vbox.restore_snapshot(vm_name, snapshot_name)


@app.post("/vms/{vm_name}/shared-folders/{shared_folder}")
def configure_shared_folder(
    vm_name: str,
    shared_folder: str,
    readonly: bool = False,
    mount_point: str | None = None,
) -> VMOperationResult:
    return vbox.configure_shared_folder(
        vm_name=vm_name,
        shared_folder=shared_folder,
        readonly=readonly,
        mount_point=mount_point,
    )


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT,
    )
