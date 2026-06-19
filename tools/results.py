from dataclasses import dataclass
from typing import Any, Literal


ToolStatus = Literal["ok", "error"]


@dataclass(frozen=True)
class ToolResult:
    status: ToolStatus
    data: Any = None
    error: str | None = None


    @classmethod
    def ok(cls, data: Any) -> "ToolResult":
        return cls(status="ok", data=data)


    @classmethod
    def failed(cls, error: Exception | str) -> "ToolResult":
        return cls(status="error", error=str(error))


    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "data": self.data,
            "error": self.error,
        }


@dataclass(frozen=True)
class CommandResult:
    stdout: str
    stderr: str
    returncode: int | None
    timed_out: bool = False


    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out
