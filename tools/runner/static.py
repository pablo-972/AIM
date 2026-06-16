from utils.logger import Logger
from tools.runner.base import BaseToolRunner
from core.results import ToolResult
from tools.static import (
    analyze_file,
    analyze_metadata,
    calculate_hashes,
    detect_packer,
    analyze_pe,
    analyze_strings,
    get_vt_data,
    save_threat_actor_messages,
)
from config import THREAT_ACTOR_MESSAGES_FILENAME


STATIC_TOOL_RUNNERS = {
    "file": analyze_file,
    "metadata": analyze_metadata,
    "hash": calculate_hashes,
    "packer": detect_packer,
    "strings": analyze_strings,
    "pe": analyze_pe,
    "vt": get_vt_data,
}

STATIC_AGENT_TOOL_RUNNERS = {
    "save_threat_actor_messages": save_threat_actor_messages,
}


class StaticToolRunner(BaseToolRunner):
    def __init__(self, context):
        super().__init__(context)


    def run_static(self) -> dict:
        modes = self.context.static_modes
        if "full" in modes:
            modes = STATIC_TOOL_RUNNERS.keys()
        
        results = {}
        for mode in modes:
            Logger.info(f"Executing {mode}")
            try:
                data = STATIC_TOOL_RUNNERS[mode](str(self.context.sample))
                results[mode] = ToolResult.ok(data).to_dict()
            except Exception as exc:
                Logger.error(f"{mode} failed: {exc}")
                results[mode] = ToolResult.failed(exc).to_dict()
        return results


    def execute_agent_tool(self, tool_name: str, parameters: dict, context: dict | None = None) -> dict:
        tool = STATIC_AGENT_TOOL_RUNNERS.get(tool_name)
        if tool is None:
            return {"error": f"Unknown static agent tool: {tool_name}"}

        parameters = dict(parameters or {})
        context = context or {}
        parameters.update(context)

        return tool(path=self.context.output, filename=THREAT_ACTOR_MESSAGES_FILENAME, parameters=parameters)
