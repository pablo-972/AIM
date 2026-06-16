from utils.io.files import save_json


class AgentMemory:
    def __init__(self, output_dir: str, filename: str, flush_interval: int | None = None):
        self.output_dir = output_dir
        self.filename = filename
        self.flush_interval = flush_interval
        self._pending_records = 0
        self.data = {"steps": []}


    def record(self, decision: dict, tool_name: str | None = None, tool_output: dict | None = None) -> None:
        self.data["steps"].append(
            {
                "agent_decision": decision,
                "tool_executed": tool_name,
                "tool_output": tool_output,
            }
        )
        self._pending_records += 1
        if self.flush_interval and self._pending_records >= self.flush_interval:
            self.flush()


    def flush(self) -> None:
        if self._pending_records == 0:
            return

        save_json(self.output_dir, self.filename, self.data)
        self._pending_records = 0
