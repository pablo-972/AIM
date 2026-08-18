from pathlib import Path
from typing import Any

from core.utils.io.files import save_json


DEFAULT_DYNAMIC_INFERENCE_FLUSH_INTERVAL = 5


class DynamicInferenceMemory:
    def __init__(
        self,
        output_dir: str | Path,
        filename: str,
        name: str,
        flush_interval: int = DEFAULT_DYNAMIC_INFERENCE_FLUSH_INTERVAL,
    ) -> None:
        self.output_dir = output_dir
        self.filename = filename
        self.flush_interval = max(1, flush_interval)
        self._pending_events = 0
        self.data: dict[str, Any] = {
            "name": name,
            "status": "running",
            "findings_count": 0,
            "steps": [],
            "findings": [],
            "errors": [],
        }
        self.flush(force=True)

    def record(
        self,
        input_ref: dict[str, Any],
        analysis: dict[str, Any],
        finding: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        steps = self.data["steps"]
        step_number = len(steps) + 1
        normalized_analysis = self._normalize_analysis(analysis)

        step = {
            "step": step_number,
            "input": input_ref,
            "analysis": normalized_analysis,
            "finding": finding,
            "error": error,
        }
        steps.append(step)

        if finding is not None:
            self.data["findings"].append(
                {
                    "step": step_number,
                    **finding,
                }
            )

        if error:
            self.data["errors"].append(
                {
                    "step": step_number,
                    "message": error,
                }
            )

        self._update_findings_count()
        self._mark_dirty()

    def fail(self, error: str) -> None:
        self.data["status"] = "error"
        self.data["errors"].append(
            {
                "step": None,
                "message": error,
            }
        )
        self._update_findings_count()
        self.flush(force=True)

    def close(self, status: str = "completed") -> None:
        self.data["status"] = status
        self._update_findings_count()
        self.flush(force=True)

    def flush(self, force: bool = False) -> None:
        if not force and self._pending_events < self.flush_interval:
            return

        save_json(self.output_dir, self.filename, self.data)
        self._pending_events = 0

    def _normalize_analysis(self, analysis: dict[str, Any]) -> dict[str, Any]:
        thought = analysis.get("thought")
        if not isinstance(thought, str):
            thought = ""

        confidence = analysis.get("confidence")
        if confidence not in {"low", "medium", "high"}:
            confidence = "unknown"

        return {
            "thought": thought,
            "confidence": confidence,
        }

    def _update_findings_count(self) -> None:
        self.data["findings_count"] = len(self.data["findings"])

    def _mark_dirty(self) -> None:
        self._pending_events += 1
        self.flush()
