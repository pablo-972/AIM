import json

from exceptions import ToolError
from utils.io.commands import run_command


def analyze_metadata(sample: str) -> str:
    result = run_command(["exiftool", "-j", str(sample)])
    if result.timed_out:
        raise ToolError("exiftool command timed out")
    if not result.ok:
        raise ToolError(result.stderr or f"exiftool failed with code {result.returncode}")

    return json.loads(result.stdout.strip())
    
