from collections.abc import Callable
from typing import Any

from tools.dynamic.analyzers.job import (
    build_dynamic_job,
    parse_dynamic_artifacts,
    prepare_dynamic_files,
    wait_for_dynamic_artifacts,
)
from tools.dynamic.manual import DYNAMIC_MANUAL_TOOLS
from tools.dynamic.virtualbox.session import VirtualBoxSession
from tools.results import ToolResult
from tools.runner.base import BaseToolRunner
from utils.logger import Logger


class DynamicToolRunner(BaseToolRunner):
    ALLOWED_RUNNERS = {"run_dynamic"}
    DYNAMIC_RESULT_TIMEOUT = 300

    def run_dynamic(self) -> dict[str, dict[str, Any]]:
        try:
            session = VirtualBoxSession.from_env()
        except Exception as exc:
            Logger.error(f"Dynamic VM session setup failed: {exc}")

            result = ToolResult.failed(exc).to_dict()
            return {"session": result}

        if self.context.dynamic_start:
            return self._start(session)

        if self.context.dynamic_stop:
            return self._stop(session)
        
        if self.context.dynamic_tools:
            return self._run_tools(session)


    def _start(self, session: VirtualBoxSession) -> dict[str, dict[str, Any]]:
        try:
            start_result = session.start()
        except Exception as exc:
            Logger.error(f"Dynamic VM start failed: {exc}")
            result = ToolResult.failed(exc).to_dict()

            return {
                "start": result
            }

        Logger.info("Dynamic VMs started.")
        result = ToolResult.ok(start_result).to_dict()

        return {
            "start": result
        }

    def _stop(self, session: VirtualBoxSession) -> dict[str, dict[str, Any]]:
        try:
            stop_result = session.stop()
        except Exception as exc:
            Logger.error(f"Dynamic VM stop failed: {exc}")
            result = ToolResult.failed(exc).to_dict()

            return {
                "stop": result
            }
        
        Logger.info("Dynamic VMs stopped.")
        result = ToolResult.ok(stop_result).to_dict()

        return {
            "stop": result
        }

    def _run_tools(self, session: VirtualBoxSession) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}
        
        try:
            start = session.prepare_tool_run()
            results["start"] = ToolResult.ok(start).to_dict()

            selected_tools = self._resolve_tools()

            config = build_dynamic_job(
                sample=self.sample,
                sha256=self.context.sample_sha256,
                selected_tools=selected_tools,
                procmon_filter=self.context.dynamic_filter,
            )

            files_data = prepare_dynamic_files(
                sample=self.sample,
                config=config,
                procmon_filter=self.context.dynamic_filter,
            )
            results["config"] = ToolResult.ok(files_data).to_dict()

            artifacts = wait_for_dynamic_artifacts(config=config, timeout=300)
            results["artifacts"] = ToolResult.ok(artifacts).to_dict()

            parsed_artifacts = parse_dynamic_artifacts(
                config=config,
                sample=self.sample,
            )
            for tool_name, data in parsed_artifacts.items():
                results[tool_name] = ToolResult.ok(data).to_dict()

        except Exception as exc:
            Logger.error(f"Dynamic tool flow failed: {exc}")
            results["error"] = ToolResult.failed(exc).to_dict()
            
        finally:
            try:
                cleanup = session.stop()
                results["cleanup"] = ToolResult.ok(cleanup).to_dict()
            except Exception as exc:
                Logger.error(f"Dynamic VM cleanup failed: {exc}")
                results["cleanup"] = ToolResult.failed(exc).to_dict()

        return results

    def _resolve_tools(self) -> list[str]:
        tools = list(self.context.dynamic_tools)
        if "full" in tools:
            return list(DYNAMIC_MANUAL_TOOLS)

        unknown_tools = []
        for tool in tools:
            if tool not in DYNAMIC_MANUAL_TOOLS:
                unknown_tools.append(tool)
        
        if unknown_tools:
            raise ValueError(f"Unknown dynamic tool(s): {', '.join(unknown_tools)}")

        return tools
