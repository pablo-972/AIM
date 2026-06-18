from typing import Any
from pathlib import Path

from config import RESULT_FILENAME
from utils.io.files import load_json, save_json


class JsonBuilder:
    def __init__(self, output_path: str, sample_path: Path, sample_sha256: str):
        self.output_path = output_path
        self.sample_path = sample_path
        existing_data = load_json(output_path, RESULT_FILENAME)
        self.data = existing_data if isinstance(existing_data, dict) else {}

        self.data["sample"] = {
            "path": str(sample_path),
            "sha256": sample_sha256,
            "size": sample_path.stat().st_size,
        }

        if not isinstance(self.data.get("phases"), dict):
            self.data["phases"] = {}


    def add_phase(self, phase_name: str, tools: dict[str, Any], status: str = "completed") -> None:
        phase = self.data["phases"].get(phase_name)
        if not isinstance(phase, dict):
            phase = {}

        existing_tools = phase.get("tools")
        if not isinstance(existing_tools, dict):
            existing_tools = {}

        existing_tools.update(tools)
        phase["status"] = status
        phase["tools"] = existing_tools
        self.data["phases"][phase_name] = phase


    def save_phase(self, phase_name: str, tools: dict[str, Any], status: str = "completed") -> None:
        self.add_phase(phase_name, tools, status)
        self.build()


    def build(self) -> None:
        save_json(self.output_path, RESULT_FILENAME, self.data)
