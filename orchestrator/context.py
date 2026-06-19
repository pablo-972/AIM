from dataclasses import dataclass
from pathlib import Path
from typing import Any

from exceptions import CLIValidationError
from utils.crypto import sha256_file


@dataclass(frozen=True)
class AnalysisContext:
    sample: Path
    sample_sha256: str
    output: Path
    output_format: str
    phase: str
    func: str | None
    static_modes: list[str]
    reversing_modes: list[str]
    value: str | None
    function: str | None
    profile: str | None
    static_agent: bool
    reversing_agent: bool


    @classmethod
    def from_args(cls, args: Any) -> "AnalysisContext":
        sample = Path(args.sample).expanduser().resolve()

        if not sample.exists():
            raise CLIValidationError(f"Sample does not exist: {sample}")

        if not sample.is_file():
            raise CLIValidationError(f"Sample is not a file: {sample}")

        sample_sha256 = sha256_file(sample)
        base_output = Path(args.output).expanduser().resolve()

        return cls(
            sample=sample,
            sample_sha256=sample_sha256,
            output=base_output / sample_sha256,
            output_format=args.format,
            phase=args.phase,
            func=getattr(args, "func", None),
            static_modes=getattr(args, "static_modes", []),
            reversing_modes=getattr(args, "reversing_modes", []),
            value=getattr(args, "value", None),
            function=getattr(args, "function", None),
            profile=getattr(args, "profile", None),
            static_agent=getattr(args, "static_agent", False),
            reversing_agent=getattr(args, "reversing_agent", False),
        )
