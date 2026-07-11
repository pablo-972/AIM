from typing import Any

EXECUTABLE = "reg.exe"
OPERATION = "export"
REGISTRY_KEYS = [
    r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon",
    r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Windows",
    r"HKLM\SYSTEM\CurrentControlSet\Services",
    r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options",
    r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Browser Helper Objects",
    r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run",
    r"HKCU\Software\Policies\Microsoft\Windows\System\Scripts\Logon",
    r"HKCU\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon",
]


def build_registry_job(
    enabled: bool,
    timeout: int,
    collect_interval_seconds: int = 60,
) -> dict[str, Any]:
    return {
        "enabled": enabled,
        "parameters": {
            "executable": EXECUTABLE,
            "operation": OPERATION,
            "registry_keys": REGISTRY_KEYS,
            "timeout": timeout,
            "collect_interval_seconds": collect_interval_seconds,
        },
    }
