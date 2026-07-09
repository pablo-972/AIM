from typing import Any


def build_autoruns_job(
    enabled: bool,
    timeout: int,
    collect_interval_seconds: int = 120,
) -> dict[str, Any]:
    return {
        "enabled": enabled,
        "parameters": {
            "timeout": timeout,
            "kill_after_timeout": True,
            "collect_interval_seconds": collect_interval_seconds,
        },
    }
