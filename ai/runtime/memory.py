from typing import Any

from utils.io.files import save_json


class AgentMemory:
    def __init__(
            self, 
            output_dir: str, 
            filename: str, 
            flush_interval: int | None = None
        ) -> None:
        self.output_dir = output_dir
        self.filename = filename
        self.flush_interval = flush_interval

        self._pending_records = 0
        self.data: dict[str, Any] = {
            "steps": [],
        }


    def record(
            self, 
            decision: dict[str, Any], 
            tool_name: str | None = None, 
            tool_output: dict[str, Any] | None = None
        ) -> None:
        steps = self.data.setdefault("steps", [])
        steps.append(
            {
                "step": len(steps) + 1,
                "decision": decision,
                "tool_executed": tool_name,
                "tool_output": tool_output,
            }
        )
        self._pending_records += 1

        if (self.flush_interval and self._pending_records >= self.flush_interval):
            self.flush()


    def flush(self) -> None:
        if self._pending_records == 0:
            return

        save_json(self.output_dir, self.filename, self.data)
        self._pending_records = 0


    def close(self) -> None:
        self.flush()
