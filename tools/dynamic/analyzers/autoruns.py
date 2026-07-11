from typing import Any

EXECUTABLE = "autorunsc.exe"
ARGUMENTS = [
    "-accepteula",
    "-nobanner",
    "-a",
    "l",
    "-c",
]

def build_autoruns_job(
    enabled: bool,
    timeout: int,
    collect_interval_seconds: int = 60,
) -> dict[str, Any]:
    return {
        "enabled": enabled,
        "parameters": {
            "executable": EXECUTABLE,
            "arguments": ARGUMENTS,
            "timeout": timeout,
            "collect_interval_seconds": collect_interval_seconds,
        },
    }
