from dataclasses import dataclass
from typing import Any

from config import get_env
from tools.dynamic.virtualbox.client import VirtualBoxAPIClient
from utils.virtualbox.contracts import VMOperationResult


VICTIM_VM = get_env("AIM_DYNAMIC_VICTIM_VM")
VICTIM_SNAPSHOT = get_env("AIM_DYNAMIC_VICTIM_SNAPSHOT")
ANALYSIS_VM = get_env("AIM_DYNAMIC_ANALYSIS_VM")
ANALYSIS_SHARED_MOUNT_POINT = get_env("AIM_DYNAMIC_ANALYSIS_SHARED_MOUNT_POINT")

VM_TIMEOUT_SECONDS = 600


@dataclass(frozen=True)
class DynamicMachines:
    victim_vm: str
    victim_snapshot: str
    analysis_vm: str


class VirtualBoxSession:
    def __init__(
        self,
        machines: DynamicMachines,
        api_client: "VirtualBoxAPIClient",
        timeout: int = VM_TIMEOUT_SECONDS,
    ) -> None:
        self.machines = machines
        self.api_client = api_client
        self.timeout = timeout

    @classmethod
    def from_env(cls, timeout: int = VM_TIMEOUT_SECONDS) -> "VirtualBoxSession":
        return cls(
            machines=DynamicMachines(
                victim_vm=VICTIM_VM,
                victim_snapshot=VICTIM_SNAPSHOT,
                analysis_vm=ANALYSIS_VM,
            ),
            timeout=timeout,
            api_client=VirtualBoxAPIClient(timeout),
        )


    def start(self) -> dict[str, Any]:
        running_vms = set(self.api_client.running_vms())
        analysis_running = self.machines.analysis_vm in running_vms
        victim_running = self.machines.victim_vm in running_vms

        result: dict[str, Any] = {}
        shared_folders: dict[str, VMOperationResult] = {}

        if not victim_running:
            result["restore_snapshot"] = self._restore_victim_snapshot()
            shared_victim = self._configure_victim_shared_folder()
            shared_folders["victim"] = (shared_victim)

        if not analysis_running:
            shared_analysis = self._configure_analysis_shared_folder()
            shared_folders["analysis"] = (shared_analysis)

        if shared_folders:
            result["shared_folders"] = shared_folders

        result["started"] = self._start_machines()

        return result

    def prepare_tool_run(self) -> dict[str, Any]:
        restored = self._restore_victim_snapshot()

        shared_victim = self._configure_victim_shared_folder()
        shared_folders = {
            "victim": shared_victim,
        }

        if not self._is_running(self.machines.analysis_vm):
            shared_analysis = self._configure_analysis_shared_folder()
            shared_folders["analysis"] = (shared_analysis)

        return {
            "restore_snapshot": restored,
            "shared_folders": shared_folders,
            "started": self._start_machines(),
        }

    def stop(self) -> dict[str, Any]:
        analysis_data = self._poweroff(self.machines.analysis_vm)
        victim_data = self._poweroff(self.machines.victim_vm)
        
        return {
            "analysis": analysis_data,
            "victim": victim_data,
        }


    def _restore_victim_snapshot(self) -> VMOperationResult:
        if self._is_running(self.machines.victim_vm):
            self._poweroff(self.machines.victim_vm)

        result = self.api_client.restore_snapshot(
            self.machines.victim_vm,
            self.machines.victim_snapshot,
        )

        return result

    def _start_machines(self) -> dict[str, VMOperationResult]:
        analysis_state = self._ensure_running(self.machines.analysis_vm)
        victim_state = self._ensure_running(self.machines.victim_vm)

        return {
            "analysis": analysis_state,
            "victim": victim_state,
        }

    def _configure_analysis_shared_folder(self) -> VMOperationResult:
        return self.api_client.configure_shared_folder(
            self.machines.analysis_vm,
            readonly=False,
            mount_point=ANALYSIS_SHARED_MOUNT_POINT,
        )

    def _configure_victim_shared_folder(self) -> VMOperationResult:
        return self.api_client.configure_shared_folder(
            self.machines.victim_vm,
            readonly=True,
        )

    def _ensure_running(self, vm_name: str) -> VMOperationResult:
        return self.api_client.start_vm(vm_name)

    def _poweroff(self, vm_name: str) -> VMOperationResult:
        return self.api_client.poweroff_vm(vm_name)

    def _is_running(self, vm_name: str) -> bool:
        return vm_name in self.api_client.running_vms()


