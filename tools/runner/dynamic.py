from typing import Any

from utils.logger import Logger
from tools.dynamic.manual import DYNAMIC_MANUAL_TOOLS
from tools.dynamic.analyzers.config import (
    build_dynamic_job,
    check_collector_health,
    prepare_dynamic_job_files,
    wait_for_dynamic_result,
)
from tools.results import ToolResult
from tools.runner.base import BaseToolRunner
from tools.dynamic.virtualbox.session import VirtualBoxSession


class DynamicToolRunner(BaseToolRunner):
    ALLOWED_RUNNERS = {"run_dynamic"}

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
            machine_state = session.prepare_tool_run()
            results["machines"] = ToolResult.ok(machine_state).to_dict()

            selected_tools = self._resolve_tools()
            job = build_dynamic_job(
                sample=self.sample,
                analysis_id=self.context.sample_sha256,
                selected_tools=selected_tools,
            )
            controller = job["controller"]
            results["collector"] = ToolResult.ok(
                check_collector_health(
                    controller["base_url"],
                    controller["timeout"],
                )
            ).to_dict()
            results["job"] = ToolResult.ok(
                prepare_dynamic_job_files(
                    sample=self.sample,
                    analysis_id=self.context.sample_sha256,
                    job=job,
                )
            ).to_dict()
            results["dynamic_result"] = ToolResult.ok(
                wait_for_dynamic_result(
                    analysis_id=self.context.sample_sha256,
                    timeout=VM_TIMEOUT_SECONDS,
                )
            ).to_dict()
        except Exception as exc:
            Logger.error(f"Dynamic tool flow failed: {exc}")
            results.setdefault("machines", ToolResult.failed(exc).to_dict())
        finally:
            try:
                results["cleanup"] = ToolResult.ok(session.stop()).to_dict()
            except Exception as exc:
                Logger.error(f"Dynamic VM cleanup failed: {exc}")
                results["cleanup"] = ToolResult.failed(exc).to_dict()

        return results

    def _resolve_tools(self) -> list[str]:
        tools = list(self.context.dynamic_tools)
        if "full" in tools:
            return list(DYNAMIC_MANUAL_TOOLS)

        unknown_tools = [
            tool
            for tool in tools
            if tool not in DYNAMIC_MANUAL_TOOLS
        ]
        if unknown_tools:
            raise ValueError(f"Unknown dynamic tool(s): {', '.join(unknown_tools)}")

        return tools
