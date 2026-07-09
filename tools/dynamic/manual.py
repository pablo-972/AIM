from collections.abc import Callable
from typing import Any

from tools.dynamic.analyzers.autoruns import build_autoruns_job
from tools.dynamic.analyzers.regshot import build_regshot_job

DynamicJobBuilder = Callable[[bool, int, int], dict[str, Any]]
DEFAULT_TOOL_TIMEOUT_SECONDS = 300
DEFAULT_COLLECT_INTERVAL_SECONDS = 120


DYNAMIC_MANUAL_TOOLS: dict[str, DynamicJobBuilder] = {
    "autoruns": build_autoruns_job,
    "regshot": build_regshot_job,
}


def build_dynamic_tools_config(
    selected_tools: list[str],
    timeout: int = DEFAULT_TOOL_TIMEOUT_SECONDS,
    collect_interval_seconds: int = DEFAULT_COLLECT_INTERVAL_SECONDS,
) -> dict[str, Any]:
    enabled_tools = set(DYNAMIC_MANUAL_TOOLS) if "full" in selected_tools else set(selected_tools)

    return {
        tool_name: builder(
            enabled=tool_name in enabled_tools,
            timeout=timeout,
            collect_interval_seconds=collect_interval_seconds,
        )
        for tool_name, builder in DYNAMIC_MANUAL_TOOLS.items()
    }
