from exceptions import ToolError
from utils.io.commands import run_command


def analyze_file(sample: str) -> str:
    result = run_command(["file", "-b", str(sample)])

    if result.timed_out:
        raise ToolError("file command timed out")
    if not result.ok:
        raise ToolError(result.stderr or f"file command failed with code {result.returncode}")

    return result.stdout.strip()

