import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from config import SHARED_FOLDER, VBOXMANAGE_PATH
from exceptions import VirtualBoxError
from utils.io.commands import run_command
from utils.virtualbox.commands import sanitize_path_for_windows
from utils.virtualbox.contracts import (
    RunningVMsResult,
    VMOperationResult,
    operation_result,
)
from utils.virtualbox.parsers import (
    SharedFolder,
    parse_running_vm_names,
    parse_shared_folder,
)
from tools.results import CommandResult

COMMAND_TIMEOUT_SECONDS = 30
GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS = 60
GRACEFUL_SHUTDOWN_POLL_SECONDS = 2


@dataclass(frozen=True)
class VirtualBoxManager:
    shared_path: Path
    vboxmanage_path: str = VBOXMANAGE_PATH
    timeout: int = COMMAND_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        self.shared_path.mkdir(parents=True, exist_ok=True)

        object.__setattr__(
            self,
            "shared_path",
            sanitize_path_for_windows(self.shared_path),
        )


    def health(self) -> dict[str, str]:
        return {
            "status": "ok",
            "vboxmanage": self.vboxmanage_path,
            "shared_dir": str(self.shared_path),
        }

    def running_vms(self) -> RunningVMsResult:
        args = ["list", "runningvms"]
        result = self._run(args)

        self._require_success(result, "Could not list running VMs")
        running_vm_names = parse_running_vm_names(result.stdout)

        return {
            "running_vms": running_vm_names
        }

    def start_vm(self, vm_name: str) -> VMOperationResult:
        if self._is_vm_running(vm_name):
            return operation_result(
                action="start",
                vm=vm_name,
                status="already_running",
                changed=False,
            )

        args = ["startvm", vm_name, "--type", "headless"]
        result = self._run(args)

        self._require_success(result, f"Could not start {vm_name}")

        return operation_result(
            action="start",
            vm=vm_name,
            status="completed",
            changed=True,
        )

    def poweroff_vm(self, vm_name: str) -> VMOperationResult:
        if not self._is_vm_running(vm_name):
            return operation_result(
                action="stop",
                vm=vm_name,
                status="already_stopped",
                changed=False,
            )

        acpi_args = ["controlvm", vm_name, "acpipowerbutton"]
        acpi_result = self._run(acpi_args)
        
        stopped_gracefully = (
            acpi_result.ok
            and self._wait_until_stopped(vm_name)
        )
        
        if stopped_gracefully:
            return operation_result(
                action="stop",
                vm=vm_name,
                status="completed",
                changed=True,
                details={
                    "method": "acpipowerbutton",
                },
            )

        fallback_args = ["controlvm", vm_name, "poweroff"]
        fallback_result = self._run(fallback_args)

        self._require_success(
            fallback_result,
            f"Could not power off {vm_name}",
            extra={"acpi": acpi_result.to_dict()},
        )

        return operation_result(
            action="stop",
            vm=vm_name,
            status="completed",
            changed=True,
            details={
                "method": "poweroff",
            },
        )

    def restore_snapshot( self, vm_name: str, snapshot_name: str) -> VMOperationResult:
        args = ["snapshot", vm_name, "restore", snapshot_name]
        result = self._run(args)
        
        self._require_success(
            result,
            f"Could not restore snapshot {snapshot_name}",
        )

        return operation_result(
            action="restore_snapshot",
            vm=vm_name,
            status="completed",
            changed=True,
            details={
                "snapshot": snapshot_name,
            },
        )

    def configure_shared_folder(
        self,
        vm_name: str,
        readonly: bool = False,
        mount_point: str | None = None,
    ) -> VMOperationResult:
        if self._is_vm_running(vm_name):
            raise VirtualBoxError(
                {
                    "message": (
                        f"Could not configure shared folder for {vm_name}: "
                        "the VM must be stopped"
                    ),
                },
                status_code=409,
            )

        desired_hostpath = str(self.shared_path)
        existing = self._get_shared_folder(vm_name)

        if existing:
            already_ok = (
                existing.hostpath == desired_hostpath
                and existing.readonly == readonly
                and existing.automount
                and existing.mount_point == mount_point
            )

            if already_ok:
                return operation_result(
                    action="configure_shared_folder",
                    vm=vm_name,
                    status="already_configured",
                    changed=False,
                    details={"shared_folder": asdict(existing)},
                )
            
            remove_result = self._remove_shared_folder(vm_name)
        else:
            remove_result = None

        self._add_shared_folder(
            vm_name=vm_name,
            hostpath=desired_hostpath,
            readonly=readonly,
            mount_point=mount_point,
        )

        details: dict[str, Any] = {
            "shared_folder": {
                "name": SHARED_FOLDER,
                "hostpath": desired_hostpath,
                "readonly": readonly,
                "automount": True,
                "mount_point": mount_point,
            },
        }

        if remove_result is not None:
            details["remove_command"] = remove_result.to_dict()

        return operation_result(
            action="configure_shared_folder",
            vm=vm_name,
            status="completed",
            changed=True,
            details=details,
        )


    def _is_vm_running(self, vm_name: str) -> bool:
        args = ["showvminfo", vm_name, "--machinereadable"]
        result = self._run(args)
        
        self._require_success(
            result,
            f"Could not read VM state for {vm_name}",
        )

        running_vms = parse_running_vm_names(result.stdout)
        return vm_name in running_vms
    

    def _wait_until_stopped(
        self,
        vm_name: str,
        timeout: int = GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS,
    ) -> bool:
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            if not self._is_vm_running(vm_name):
                return True
            time.sleep(GRACEFUL_SHUTDOWN_POLL_SECONDS)

        return not self._is_vm_running(vm_name)


    def _remove_shared_folder(
        self,
        vm_name: str,
    ) -> CommandResult:
        args = [
            "sharedfolder",
            "remove",
            vm_name,
            "--name",
            SHARED_FOLDER,
        ]

        result = self._run(args)
        
        stderr = result.stderr
        ignored_errors = ["does not exist", "is not currently running"]

        if result.returncode != 0:
            for error in ignored_errors:
                if error in stderr:
                    return result

            self._require_success(
                result,
                f"Could not remove shared folder from {vm_name}",
            )

        return result

    def _add_shared_folder(
        self,
        vm_name: str,
        hostpath: str,
        readonly: bool,
        mount_point: str | None,
    ) -> CommandResult:
        shared_folder_args = _build_shared_folder_add_args(
            vm_name=vm_name,
            folder_name=SHARED_FOLDER,
            hostpath=hostpath,
            readonly=readonly,
            mount_point=mount_point,
        )
        result = self._run(shared_folder_args)
        self._require_success(
            result,
            f"Could not configure shared folder for {vm_name}",
        )

        return result
    
    def _get_shared_folder(self, vm_name: str) -> SharedFolder | None:
        args = ["showvminfo", vm_name, "--machinereadable"]
        result = self._run(args)

        self._require_success(
            result,
            f"Could not read shared folders for {vm_name}",
        )

        shared_folder = parse_shared_folder(result.stdout, SHARED_FOLDER)
        return shared_folder


    def _run(self, args: list[str]) -> CommandResult:
        command = [self.vboxmanage_path, *args]

        result = run_command(command, timeout=self.timeout)
        return result 


    @staticmethod
    def _require_success(
        result: CommandResult,
        message: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        if result.ok:
            return

        detail: dict[str, Any] = {
            "message": message,
            "command": result.to_dict(),
        }
        if extra:
            detail.update(extra)

        status_code = 500
        if result.timed_out:
            status_code = 504

        raise VirtualBoxError(detail, status_code=status_code)


def _build_shared_folder_add_args(
    vm_name: str,
    folder_name: str,
    hostpath: str,
    readonly: bool,
    mount_point: str | None = None,
) -> list[str]:
    args = [
        "sharedfolder",
        "add",
        vm_name,
        "--name",
        folder_name,
        "--hostpath",
        hostpath,
        "--automount",
    ]

    if mount_point:
        args.extend(["--auto-mount-point", mount_point])
    if readonly:
        args.append("--readonly")

    return args
