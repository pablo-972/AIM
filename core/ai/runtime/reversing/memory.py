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
            "summary": {
                "steps": 0,
                "findings": 0,
                "queue_events": 0,
                "errors": 0,
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

        self._update_summary()
        save_json(self.output_dir, self.filename, self.data)
        self._pending_events = 0

    def _mark_dirty(self) -> None:
        self._pending_events += 1
        self.flush()

    def _update_summary(self) -> None:
        self.data["summary"] = self._summary()

    def _summary(self) -> dict[str, int]:
        steps = self.data.get("steps", [])
        findings = self.data.get("findings", [])
        queue = self.data.get("queue", [])
        errors = self.data.get("errors", [])

        return {
            "steps": len(steps),
            "findings": len(findings),
            "queue_events": len(queue),
            "errors": len(errors),
        }
