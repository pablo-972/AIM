from pathlib import Path

from core.exceptions import VirtualBoxError
from core.utils.io.commands import run_command


def sanitize_path_for_windows(path: str | Path) -> Path:
    path_str = str(path)

    if not path_str.startswith("/"):
        return Path(path_str)

    command = ["wslpath", "-w", path_str]
    result = run_command(command)

    if not result.ok:
        status_code = 500
        if result.timed_out:
            status_code = 504

        raise VirtualBoxError(
            {
                "message": f"Could not convert path for Windows: {path_str}",
                "command": result.to_dict(),
            },
            status_code=status_code,
        )

    sanitized = result.stdout.strip()
    if not sanitized:
        raise VirtualBoxError(
            f"wslpath returned an empty path for: {path_str}",
            status_code=500,
        )

    return Path(sanitized)
