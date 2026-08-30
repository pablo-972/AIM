from pathlib import Path
from typing import Any

from core.ai.runtime.reversing.trace_formatter import ReversingTraceFormatter
from core.utils.io.files import save_json

DEFAULT_REVERSING_AGENT_FLUSH_INTERVAL = 5


class ReversingAgentMemory:
    def __init__(
        self,
        output_dir: str | Path,
        filename: str,
        name: str,
        flush_interval: int = DEFAULT_REVERSING_AGENT_FLUSH_INTERVAL,
    ) -> None:
        self.output_dir = output_dir
        self.filename = filename
        self.flush_interval = max(1, flush_interval)
        self.formatter = ReversingTraceFormatter()
        self._pending_events = 0
        self.data: dict[str, Any] = {
            "agent": name,
            "status": "running",
            "state": {
                "steps": 0,
                "findings": 0,
                "errors": 0,
                "hypothesis": {
                    "type": "unknown",
                    "confidence": "low",
                },
                "coverage": {
                    "entrypoint": "unexplored",
                    "functions": "unexplored",
                    "imports": "unexplored",
                    "sections": "unexplored",
                },
                "queue": {
                    "pending": 0,
                },
            },
            "steps": [],
            "findings": [],
            "queue": [],
            "errors": [],
        }
        self.flush(force=True)

    def record(
        self,
        decision: dict[str, Any],
        tool_name: str | None = None,
        tool_parameters: dict[str, Any] | None = None,
        tool_output: dict[str, Any] | None = None,
        input_ref: dict[str, Any] | None = None,
        finding: dict[str, Any] | None = None,
        follow_ups: list[dict[str, Any]] | None = None,
        error: str | None = None,
    ) -> None:
        steps = self.data["steps"]
        step_number = len(steps) + 1
        step = self.formatter.step(
            step_number=step_number,
            decision=decision,
            tool_name=tool_name,
            tool_parameters=tool_parameters,
            tool_output=tool_output,
            input_ref=input_ref,
            finding=finding,
            follow_ups=follow_ups,
            error=error,
        )
        steps.append(step)

        if step["finding"] is not None:
            self.data["findings"].append(
                {
                    "step": step_number,
                    **step["finding"],
                }
            )

        if step["error"]:
            self.data["errors"].append(
                {
                    "step": step_number,
                    "message": step["error"],
                }
            )

        self._mark_dirty()

    def record_queue_event(
        self,
        action: str,
        target: dict[str, Any],
        queue_size: int,
        source: str,
    ) -> None:
        queue = self.data["queue"]
        queue.append(self.formatter.queue_event(
            event_number=len(queue) + 1,
            action=action,
            target=target,
            queue_size=queue_size,
            source=source,
        ))
        self._mark_dirty()

    def fail(self, error: str) -> None:
        self.data["status"] = "error"
        self.data["errors"].append(
            {
                "step": None,
                "message": error,
            }
        )
        self.flush(force=True)

    def close(self, status: str = "completed") -> None:
        self.data["status"] = status
        self.flush(force=True)

    def flush(self, force: bool = False) -> None:
        if not force and self._pending_events < self.flush_interval:
            return

        self._update_state()
        save_json(self.output_dir, self.filename, self.data)
        self._pending_events = 0

    def _mark_dirty(self) -> None:
        self._pending_events += 1
        self.flush()

    def _update_state(self) -> None:
        self.data["state"] = self.state()

    def state(self, pending_queue: int | None = None) -> dict[str, Any]:
        steps = self.data.get("steps", [])
        findings = self.data.get("findings", [])
        queue = self.data.get("queue", [])
        errors = self.data.get("errors", [])

        pending = self._pending_queue_size(queue, pending_queue)
        return {
            "steps": len(steps),
            "findings": len(findings),
            "errors": len(errors),
            "hypothesis": self._hypothesis(findings),
            "coverage": self._coverage(steps, queue),
            "queue": {
                "pending": pending,
            },
        }

    def _pending_queue_size(
        self,
        queue: Any,
        pending_queue: int | None,
    ) -> int:
        if isinstance(pending_queue, int):
            return max(0, pending_queue)

        if not isinstance(queue, list) or not queue:
            return 0

        last_event = queue[-1]
        if not isinstance(last_event, dict):
            return 0

        queue_size = last_event.get("queue_size")
        return queue_size if isinstance(queue_size, int) and queue_size >= 0 else 0

    def _hypothesis(self, findings: Any) -> dict[str, str]:
        if not isinstance(findings, list) or not findings:
            return {
                "type": "unknown",
                "confidence": "low",
            }

        categories = {
            finding.get("category")
            for finding in findings
            if isinstance(finding, dict)
        }
        if categories.intersection({"file_encryption", "crypto"}):
            return {
                "type": "ransomware",
                "confidence": "medium",
            }
        if "network" in categories:
            return {
                "type": "network-capable malware",
                "confidence": "low",
            }

        return {
            "type": "malware behavior",
            "confidence": "low",
        }

    def _coverage(self, steps: Any, queue: Any) -> dict[str, str]:
        tools = self._executed_tools(steps)
        sources = self._queue_sources(queue)

        return {
            "entrypoint": (
                "explored"
                if "baseline_entrypoint" in sources or "disassembly" in tools
                else "unexplored"
            ),
            "functions": self._partial_if_any(
                tools,
                {"list_functions", "disassembly", "callers", "callees"},
            ),
            "imports": self._partial_if_any(
                tools,
                {"list_imports", "import_xrefs"},
            ),
            "sections": self._partial_if_any(
                tools,
                {"list_sections", "inspect_section"},
            ),
        }

    def _executed_tools(self, steps: Any) -> set[str]:
        if not isinstance(steps, list):
            return set()

        tools = set()
        for step in steps:
            if not isinstance(step, dict):
                continue

            input_data = step.get("input")
            if not isinstance(input_data, dict):
                continue

            tool = input_data.get("tool")
            if isinstance(tool, str):
                tools.add(tool)

        return tools

    def _queue_sources(self, queue: Any) -> set[str]:
        if not isinstance(queue, list):
            return set()

        sources = set()
        for event in queue:
            if not isinstance(event, dict):
                continue

            source = event.get("source")
            if isinstance(source, str):
                sources.add(source)

        return sources

    def _partial_if_any(self, tools: set[str], relevant: set[str]) -> str:
        return "partial" if tools.intersection(relevant) else "unexplored"
