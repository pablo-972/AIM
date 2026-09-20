import os
import platform

from core.utils.wsl import is_wsl


DEFAULT_WINDOWS_VBOXMANAGE_PATH = r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
DEFAULT_WSL_VBOXMANAGE_PATH = "/mnt/c/Program Files/Oracle/VirtualBox/VBoxManage.exe"


def get_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Environment variable '{name}' is required")

    return value


def get_optional_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default

    return value


def get_env_int(name: str, default: int | None = None) -> int:
    value = get_optional_env(name)
    if value is None:
        if default is not None:
            return default
        raise RuntimeError(f"Environment variable '{name}' is required")

    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(
            f"Environment variable '{name}' must be an integer"
        ) from exc


def default_vboxmanage_path() -> str:
    if platform.system().lower() == "windows":
        return DEFAULT_WINDOWS_VBOXMANAGE_PATH

    if is_wsl():
        return DEFAULT_WSL_VBOXMANAGE_PATH

    return "VBoxManage"
