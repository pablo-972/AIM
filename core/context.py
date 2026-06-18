from dataclasses import dataclass
from pathlib import Path

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
    profile: str | None
    static_agent: bool
    

    @classmethod
    def from_args(cls, args):
        sample = Path(args.sample).expanduser().resolve()

        if not sample.exists():
            raise CLIValidationError(f"Sample does not exist: {sample}")

        if not sample.is_file():
            raise CLIValidationError(f"Sample is not a file: {sample}")

        sample_sha256 = sha256_file(sample)
        base_output = Path(args.output).expanduser().resolve()
        output = base_output / sample_sha256

        return cls(
            sample=sample,
            output=output,
            output_format=args.format,
            phase=args.phase,
            func=getattr(args, "func", None),
            profile=getattr(args, "profile", None),
            static_modes=getattr(args, "static_modes", []),
            static_agent=getattr(args, "static_agent", False),
            sample_sha256=sample_sha256,
        )