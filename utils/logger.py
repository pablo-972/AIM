from datetime import datetime
from pathlib import Path


class Logger:
    RESET = "\033[0m"
    INFO = "\033[94m"      # Blue
    SUCCESS = "\033[92m"   # Green
    WARNING = "\033[93m"   # Yellow
    ERROR = "\033[91m"     # Red
    DEBUG = "\033[90m"     # Gray

    LOG_FILE = Path("logs/aim.log")

    @classmethod
    def _write_file(cls, line: str) -> None:
        cls.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(cls.LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    @classmethod
    def _log(cls, level: str, color: str, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file_line = f"[{timestamp}] [{level}] {message}"
        console_line = (
            f"[{timestamp}] "
            f"[{color}{level}{cls.RESET}] "
            f"{message}"
        )
        print(console_line)
        cls._write_file(file_line)

    @classmethod
    def info(cls, message: str) -> None:
        cls._log("INFO", cls.INFO, message)

    @classmethod
    def success(cls, message: str) -> None:
        cls._log("SUCCESS", cls.SUCCESS, message)

    @classmethod
    def warning(cls, message: str) -> None:
        cls._log("WARNING", cls.WARNING, message)

    @classmethod
    def error(cls, message: str) -> None:
        cls._log("ERROR", cls.ERROR, message)

    @classmethod
    def debug(cls, message: str) -> None:
        cls._log("DEBUG", cls.DEBUG, message)