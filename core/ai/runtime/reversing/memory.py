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
            "hypothesis": {
                "malware": None,
                "type": None,
                "confidence": "low",
            },
            "state": {
                "steps": 0,
                "findings": 0,
                "errors": 0,
                "discovery": {
                    "entrypoints": False,
                    "functions": False,
                    "imports": False,
                    "sections": False,
                },
                "explored": {
                    "functions": 0,
                    "imports": 0,
                    "sections": 0,
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
        tool_calls: list[dict[str, Any]] | None = None,
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
            tool_calls=tool_calls,
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

    def hypothesis(self) -> dict[str, Any]:
        value = self.data.get("hypothesis")
        return self._normalized_hypothesis(value) or {
            "malware": None,
            "type": None,
            "confidence": "low",
        }

    def update_hypothesis(self, hypothesis: Any) -> None:
        normalized = self._normalized_hypothesis(hypothesis)
        if normalized is None:
            return

        self.data["hypothesis"] = normalized

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
            "discovery": self._discovery(steps),
            "explored": self._explored(steps),
            "queue": {
                "pending": pending,
            },
        }

    def global_review_state(self) -> dict[str, Any]:
        state = self.state(pending_queue=0)
        return {
            "steps": state["steps"],
            "findings": state["findings"],
            "errors": state["errors"],
            "discovery": state["discovery"],
            "explored": state["explored"],
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

    def _normalized_hypothesis(self, value: Any) -> dict[str, Any] | None:
        if not isinstance(value, dict):
            return None

        malware = value.get("malware")
        if malware is not True and malware is not False and malware is not None:
            malware = None

        hypothesis_type = value.get("type")
        if hypothesis_type is not None:
            if isinstance(hypothesis_type, str) and hypothesis_type.strip():
                hypothesis_type = hypothesis_type.strip()
            else:
                hypothesis_type = None

        confidence = value.get("confidence")
        if confidence not in {"low", "medium", "high"}:
            confidence = "low"

        return {
            "malware": malware,
            "type": hypothesis_type,
            "confidence": confidence,
        }


    def _discovery(self, steps: Any) -> dict[str, bool]:
        tools = self._executed_tools(steps)
        return {
            "entrypoints": "list_entrypoints" in tools,
            "functions": "list_functions" in tools,
            "imports": "list_imports" in tools,
            "sections": "list_sections" in tools,
        }

    def _explored(self, steps: Any) -> dict[str, int]:
        return {
            "functions": len(self._explored_targets(
                steps,
                {"disassembly", "callers", "callees"},
            )),
            "imports": len(self._explored_targets(steps, {"import_xrefs"})),
            "sections": len(self._explored_targets(steps, {"inspect_section"})),
        }

    def _explored_targets(self, steps: Any, tools: set[str]) -> set[str]:
        targets = set()
        for input_data in self._step_inputs(steps):
            tool = input_data.get("tool")
            if tool not in tools:
                continue

            status = input_data.get("status")
            if status == "error":
                continue

            target = input_data.get("target")
            targets.add(str(target) if target is not None else str(input_data))

        return targets

    def _executed_tools(self, steps: Any) -> set[str]:
        return {
            tool
            for input_data in self._step_inputs(steps)
            for tool in (input_data.get("tool"),)
            if isinstance(tool, str)
        }

    def _step_inputs(self, steps: Any) -> list[dict[str, Any]]:
        if not isinstance(steps, list):
            return []

        inputs = []
        for step in steps:
            if not isinstance(step, dict):
                continue

            input_data = step.get("input")
            if not isinstance(input_data, dict):
                continue

            inputs.append(input_data)

        return inputs
