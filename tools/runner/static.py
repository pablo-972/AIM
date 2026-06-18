from typing import Any
from collections.abc import Callable

from config import THREAT_ACTOR_MESSAGES_FILENAME
from utils.logger import Logger
from core.results import ToolResult
from tools.runner.base import BaseToolRunner
from tools.static import (
    analyze_file,
    analyze_metadata,
    analyze_pe,
    analyze_strings,
    calculate_hashes,
    detect_packer,
    get_vt_data,
    is_pe,
    save_threat_actor_messages,
)


StaticTool = Callable[[str], dict[str, Any]]
AgentTool = Callable[..., dict[str, Any]]


STATIC_TOOL_RUNNERS: dict[str, StaticTool] = {
    "file": analyze_file,
    "metadata": analyze_metadata,
    "hash": calculate_hashes,
    "packer": detect_packer,
    "strings": analyze_strings,
    "pe": analyze_pe,
    "vt": get_vt_data,
}

STATIC_AGENT_TOOL_RUNNERS: dict[str, AgentTool] = {
    "save_threat_actor_messages": save_threat_actor_messages,
}



class StaticToolRunner(BaseToolRunner):
    ALLOWED_RUNNERS = {"run_static"}

    def __init__(self, context: Any) -> None:
        super().__init__(context)
        self.is_pe = is_pe(str(self.sample))


    def _execute_tool(self, mode: str) -> dict[str, Any]:
        Logger.info(f"Executing static tool: {mode}")
        tool = STATIC_TOOL_RUNNERS[mode]

        try:
            data = tool(str(self.sample))
            return ToolResult.ok(data).to_dict()
        except Exception as exc:
            Logger.error(f"Static tool '{mode}' failed: {exc}")
            return ToolResult.failed(exc).to_dict()


    def _resolve_modes(self) -> list[str]:
        modes = list(self.context.static_modes)
        if "full" in modes:
            return list(STATIC_TOOL_RUNNERS)

        unknown_modes = [mode for mode in modes if mode not in STATIC_TOOL_RUNNERS]
        if unknown_modes:
            raise ValueError(f"Unknown static mode(s): {', '.join(unknown_modes)}")

        return modes


    def run_static(self) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}

        for mode in self._resolve_modes():
            results[mode] = self._execute_tool(mode)

        return results

    
    def execute_agent_tool(self, tool_name: str, parameters: dict[str, Any] | None = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
        tool = STATIC_AGENT_TOOL_RUNNERS.get(tool_name)
        if tool is None:
            return {
                "success": False,
                "error": f"Unknown static agent tool: {tool_name}",
            }

        payload = {**(context or {}), **(parameters or {})}

        try:
            return tool(path=self.context.output, filename=THREAT_ACTOR_MESSAGES_FILENAME, parameters=payload)
        except Exception as exc:
            Logger.error(f"Static agent tool '{tool_name}' failed: {exc}")
            return {
                "success": False,
                "error": str(exc),
            }




