from pathlib import Path
from typing import Any

from utils.io.files import save_json

DEFAULT_TRACE_FLUSH_INTERVAL = 10
NO_TOOL_ACTIONS = {"none", "finish", "seed_queue"}
COMPACT_OUTPUT_KEYS = {
    "success",
    "saved",
    "saved_count",
    "item_id",
    "reason",
    "function",
    "resolved_function",
    "start_address",
    "end_address",
    "query",
    "target",
    "count",
    "instructions_count",
    "returned_instructions",
    "truncated",
}
LARGE_OUTPUT_KEYS = {
    "message_block",
    "items",
    "blocks",
    "disassembly",
    "instructions",
    "ops",
}


class TraceMemory:
    def __init__(
        self,
        output_dir: str | Path,
        filename: str,
        agent_name: str,
        flush_interval: int = DEFAULT_TRACE_FLUSH_INTERVAL,
    ) -> None:
        self.output_dir = output_dir
        self.filename = filename
        self.flush_interval = max(1, flush_interval)
        self._pending_events = 0
        self.data: dict[str, Any] = {
            "agent": agent_name,
            "status": "running",
            "steps": [],
            "findings": [],
            "artifacts": [],
            "queue": [],
            "errors": [],
        }

    def record(
        self,
        decision: dict[str, Any],
        tool_name: str | None = None,
        tool_output: dict[str, Any] | None = None,
        input_ref: dict[str, Any] | None = None,
        finding: dict[str, Any] | None = None,
        artifact_ref: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        steps = self.data["steps"]
        step_number = len(steps) + 1
        normalized_decision = self._normalize_decision(decision)
        normalized_decision = self._align_decision_with_tool(
            normalized_decision,
            tool_name,
        )
        normalized_error = error or self._tool_error(tool_output)

        step = {
            "step": step_number,
            "input": input_ref or {
                "type": "unknown",
                "value": None,
            },
            "decision": normalized_decision,
            "tool": self._normalize_tool(
                decision=normalized_decision,
                tool_name=tool_name,
                tool_output=tool_output,
                artifact_ref=artifact_ref,
            ),
            "finding": finding,
            "error": normalized_error,
        }
        steps.append(step)

        if finding is not None:
            self.data["findings"].append(
                {
                    **finding,
                    "step": step_number,
                }
            )

        if artifact_ref is not None and artifact_ref not in self.data["artifacts"]:
            self.data["artifacts"].append(artifact_ref)

        if normalized_error:
            self.data["errors"].append(
                {
                    "step": step_number,
                    "message": normalized_error,
                }
            )

        self._mark_dirty()

    def close(self, status: str = "completed") -> None:
        self.data["status"] = status
        self.flush(force=True)

    def record_queue_event(
        self,
        action: str,
        target: dict[str, Any],
        queue_size: int,
        source: str,
    ) -> None:
        queue = self.data["queue"]
        queue.append(
            {
                "event": len(queue) + 1,
                "action": action,
                "source": source,
                "target": target,
                "queue_size": queue_size,
            }
        )
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

    def flush(self, force: bool = False) -> None:
        if not force and self._pending_events < self.flush_interval:
            return

        save_json(self.output_dir, self.filename, self.data)
        self._pending_events = 0

    def _mark_dirty(self) -> None:
        self._pending_events += 1
        self.flush()

    def _normalize_decision(self, decision: dict[str, Any]) -> dict[str, Any]:
        confidence = decision.get("confidence")
        if confidence not in {"low", "medium", "high"}:
            confidence = "low"

        action = decision.get("action")
        if not isinstance(action, str) or not action:
            action = "none"

        parameters = decision.get("parameters")
        if not isinstance(parameters, dict):
            parameters = {}

        thought = decision.get("thought")
        if not isinstance(thought, str):
            thought = ""

        return {
            "thought": thought,
            "confidence": confidence,
            "action": action,
            "parameters": parameters,
        }

    def _align_decision_with_tool(
        self,
        decision: dict[str, Any],
        tool_name: str | None,
    ) -> dict[str, Any]:
        if (
            tool_name
            and tool_name not in NO_TOOL_ACTIONS
            and decision["action"] not in {"none", "finish", tool_name}
        ):
            decision["action"] = tool_name

        return decision

    def _normalize_tool(
        self,
        decision: dict[str, Any],
        tool_name: str | None,
        tool_output: dict[str, Any] | None,
        artifact_ref: dict[str, Any] | None,
    ) -> dict[str, Any]:
        action = decision["action"]
        if tool_name is None and tool_output is not None and action not in NO_TOOL_ACTIONS:
            tool_name = action

        if tool_name is None or tool_name in NO_TOOL_ACTIONS:
            status = "error" if tool_output is not None else "skipped"
            return {
                "name": "none",
                "status": status,
                "output": self._compact_tool_output(tool_output),
                "artifact_ref": artifact_ref,
            }

        success = tool_output.get("success") if isinstance(tool_output, dict) else False
        return {
            "name": tool_name,
            "status": "ok" if success is True else "error",
            "output": self._compact_tool_output(tool_output),
            "artifact_ref": artifact_ref,
        }

    def _compact_tool_output(
        self,
        tool_output: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(tool_output, dict):
            return None

        compact: dict[str, Any] = {}
        self._copy_compact_fields(tool_output, compact)
        self._add_collection_counts(tool_output, compact)

        data = tool_output.get("data")
        if isinstance(data, dict):
            self._copy_compact_fields(data, compact)
            self._add_collection_counts(data, compact)
        elif isinstance(data, list):
            compact["result_count"] = len(data)

        return compact or None

    def _copy_compact_fields(
        self,
        source: dict[str, Any],
        target: dict[str, Any],
    ) -> None:
        for key in COMPACT_OUTPUT_KEYS:
            value = source.get(key)
            if value is not None and not isinstance(value, (dict, list)):
                target[key] = value

        item = source.get("item")
        if isinstance(item, dict) and item.get("id") is not None:
            target["item_id"] = item["id"]

    def _add_collection_counts(
        self,
        source: dict[str, Any],
        target: dict[str, Any],
    ) -> None:
        for key, value in source.items():
            if key in LARGE_OUTPUT_KEYS and isinstance(value, (dict, list)):
                target.setdefault(f"{key}_count", len(value))
            elif isinstance(value, list):
                target.setdefault(f"{key}_count", len(value))

            if key == "matches" and isinstance(value, list):
                xrefs_count = sum(
                    len(item.get("xrefs", []))
                    for item in value
                    if isinstance(item, dict)
                    and isinstance(item.get("xrefs"), list)
                )
                target.setdefault("xrefs_count", xrefs_count)

    def _tool_error(self, tool_output: dict[str, Any] | None) -> str | None:
        if not isinstance(tool_output, dict):
            return None
        if tool_output.get("success") is not False:
            return None

        error = tool_output.get("error") or tool_output.get("reason")
        return str(error) if error else "Tool execution failed."
