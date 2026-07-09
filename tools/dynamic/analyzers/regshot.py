from typing import Any


def build_regshot_job(
    enabled: bool,
    timeout: int,
    collect_interval_seconds: int = 5,
) -> dict[str, Any]:
    return {
        "enabled": enabled,
        "parameters": {
            "timeout": timeout,
            "kill_after_timeout": True,
            "collect_interval_seconds": collect_interval_seconds,
        },
    }
