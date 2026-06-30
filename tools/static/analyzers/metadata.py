import json
from typing import Any

from exceptions import ToolError
from utils.io.commands import run_command


def analyze_metadata(sample: str) -> list[dict[str, Any]]:
    result = run_command(["exiftool", "-j", str(sample)])

    if result.timed_out:
        raise ToolError("exiftool command timed out")
    if not result.ok:
        raise ToolError(result.stderr or f"exiftool failed with code {result.returncode}")

    data = json.loads(result.stdout.strip())
    is_valid = (
        isinstance(data, list)
        and all(isinstance(item, dict) for item in data)
    )

    if not is_valid:
        raise ToolError("exiftool response must be a list of objects")

    return data
    
