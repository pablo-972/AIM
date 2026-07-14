from typing import Any
from pathlib import Path

from config import RESULT_FILENAME
from core.utils.io.files import load_json, save_json


class JsonBuilder:
    def __init__(
        self,
        output_path: str | Path,
        sample_path: Path,
        sample_sha256: str,
    ) -> None:
        self.output_path: str | Path = output_path
        self.sample_path: Path = sample_path
        self.data: dict[str, Any] = self._load_data()

        self._set_sample(sample_sha256)
        self._ensure_phases()

    def add_phase(self, phase_name: str, tools: dict[str, Any], status: str = "completed") -> None:
        phases = self.data["phases"]
        if not isinstance(phases, dict):
            phases = {}
            self.data["phases"] = phases

        phase = phases.get(phase_name)
        if not isinstance(phase, dict):
            phase = {}

        existing_tools = phase.get("tools")
        if not isinstance(existing_tools, dict):
            existing_tools = {}
            
        existing_tools.update(tools)

        phase["status"] = status
        phase["tools"] = existing_tools
        phases[phase_name] = phase

    def save_phase(self, phase_name: str, tools: dict[str, Any], status: str = "completed") -> None:
        self.add_phase(phase_name, tools, status)
        self.build()

    def build(self) -> None:
        save_json(self.output_path, RESULT_FILENAME, self.data)


    def _load_data(self) -> dict[str, Any]:
        existing_data = load_json(self.output_path, RESULT_FILENAME)
        return existing_data if isinstance(existing_data, dict) else {}
    
    def _set_sample(self, sample_sha256: str) -> None:
        self.data["sample"] = {
            "path": str(self.sample_path),
            "sha256": sample_sha256,
            "size": self.sample_path.stat().st_size,
        }

    def _ensure_phases(self) -> None:
        if not isinstance(self.data.get("phases"), dict):
            self.data["phases"] = {}