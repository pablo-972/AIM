import platform


def is_wsl() -> bool:
    release = platform.release().lower()
    if "microsoft" in release or "wsl" in release:
        return True

    version = platform.version().lower()
    return "microsoft" in version or "wsl" in version
