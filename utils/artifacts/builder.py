from typing import Any
from pathlib import Path

from config import RESULT_FILENAME
from utils.io.files import save_json


class JsonBuilder:
    def __init__(self, output_path: str, sample_path: Path):
        self.output_path = output_path
        self.sample_path = sample_path
        self.data = {
            "sample": {
                "path": str(sample_path),
                "size": sample_path.stat().st_size,
            },
            "phases": {},
        }


    def add_phase(self, phase_name: str, tools: dict[str, Any], status: str = "completed") -> None:
        self.data["phases"][phase_name] = {
            "status": status, 
            "tools": tools
        }


    def build(self) -> None:
        save_json(self.output_path, RESULT_FILENAME, self.data)
