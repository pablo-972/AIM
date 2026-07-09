import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from config import SHARED_PATH
from exceptions import VirtualBoxError
from setup.manager import VirtualBoxManager
from utils.virtualbox.contracts import (
    RunningVMsResult,
    VMOperationResult,
)

API_HOST = "0.0.0.0"
API_PORT = 8090


app = FastAPI(title="AIM VirtualBox Host API")
vbox = VirtualBoxManager(shared_path=SHARED_PATH)


@app.get("/health")
def health() -> dict[str, str]:
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


@app.post("/vms/{vm_name}/shared-folders/shared")
def configure_shared_folder(
    vm_name: str,
    readonly: bool = False,
    mount_point: str | None = None,
) -> VMOperationResult:
    result = vbox.configure_shared_folder(vm_name, readonly, mount_point)

    return result


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT,
    )
