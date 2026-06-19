import subprocess

from tools.results import CommandResult

DEFAULT_COMMAND_TIMEOUT = 30


def run_command(command: list[str], timeout: int = DEFAULT_COMMAND_TIMEOUT) -> CommandResult:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return CommandResult(
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
            returncode=None,
            timed_out=True,
        )

