import urllib.parse
from typing import Any

from config import get_env
from exceptions import HTTPError
from utils.virtualbox.contracts import (
    VMOperationResult,
    validate_operation_result,
    validate_running_vms_result,
)

import requests

VB_API_HOST = get_env("AIM_VBOXMANAGE_API_HOST")
VB_API_PORT = get_env("AIM_VBOXMANAGE_API_PORT")

VB_API_BASE_URL = f"http://{VB_API_HOST}:{VB_API_PORT}".rstrip("/")


class VirtualBoxAPIClient:
    def __init__(self, timeout: int) -> None:
        self.timeout = timeout

    def running_vms(self) -> list[str]:
        response = self._request("GET", "/vms/running")
        result = validate_running_vms_result(response)

        running_vms = result.get("running_vms") 
        return running_vms

    def start_vm(self, vm_name: str) -> VMOperationResult:
        encoded_vm_name = _url_quote(vm_name)

        response = self._request("POST", f"/vms/{encoded_vm_name}/start")

        result = validate_operation_result(response)
        return result

    def poweroff_vm(self, vm_name: str) -> VMOperationResult:
        encoded_vm_name = _url_quote(vm_name)

        response = self._request("POST", f"/vms/{encoded_vm_name}/poweroff")

        result = validate_operation_result(response)
        return result

    def restore_snapshot(self, vm_name: str, snapshot_name: str) -> VMOperationResult:
        encoded_vm_name = _url_quote(vm_name)
        encoded_snapshot_name = _url_quote(snapshot_name)

        endpoint = f"/vms/{encoded_vm_name}/snapshots/{encoded_snapshot_name}/restore"
        response = self._request("POST", endpoint)

        result = validate_operation_result(response)
        return result

    def configure_shared_folder(
        self,
        vm_name: str,
        readonly: bool,
        mount_point: str | None = None,
    ) -> VMOperationResult:
        encoded_vm_name = _url_quote(vm_name)

        params: dict[str, str | bool] = {"readonly": readonly}
        if mount_point:
            params["mount_point"] = mount_point
        
        endpoint = f"/vms/{encoded_vm_name}/shared-folders/shared"
        response = self._request("POST", endpoint=endpoint, params=params)

        result = validate_operation_result(response)
        return result 
    

    def _request(
        self,
        method: str,
        endpoint: str,
        payload: dict[str, Any] | None = None,
        params: dict[str, str | bool] | None = None,
    ) -> dict[str, Any]:
        response = requests.request(
                method=method,
                url=f"{VB_API_BASE_URL}{endpoint}",
                json=payload,
                params=params,
                timeout=self.timeout,
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise HTTPError(
                f"VirtualBox API returned HTTP {response.status_code}: "
                f"{_safe_response_text(response)}"
            ) from exc

        data = {}

        try:
            if response.content:
                data = response.json() 
        except ValueError as exc:
            raise ValueError(f"VirtualBox API returned invalid JSON: {endpoint}") from exc

        if not isinstance(data, dict):
            raise ValueError(f"VirtualBox API returned a non-object response: {endpoint}")

        return data
    

def _url_quote(value: str) -> str:
    return urllib.parse.quote(value, safe="")


def _safe_response_text(response: requests.Response) -> str:
    text = response.text.strip()
    return text or "<empty response body>"



