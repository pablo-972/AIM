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
    except subprocess.TimeoutExpired as exc:
        stdout = (
            exc.stdout.decode(errors="replace") 
            if isinstance(exc.stdout, bytes) 
            else exc.stdout
        )
        stderr = (
            exc.stderr.decode(errors="replace") 
            if isinstance(exc.stderr, bytes) 
            else exc.stderr
        )

        return CommandResult(
            stdout=stdout or "",
            stderr=stderr or "",
            returncode=None,
            timed_out=True,
        )

    return CommandResult(
        stdout=result.stdout,
        stderr=result.stderr,
        returncode=result.returncode,
    )
