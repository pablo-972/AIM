from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AnalysisContext:
    sample: Path
    output: Path
    phase: str
    output_format: str
    func: str | None = None
    profile: str | None = None
    static_modes: tuple[str, ...] = ()
    static_agent: bool = False

    @classmethod
    def from_args(cls, args) -> "AnalysisContext":
        return cls(
            sample=Path(args.sample),
            output=Path(args.output),
            phase=args.phase,
            output_format=args.format,
            func=getattr(args, "func", None),
            profile=getattr(args, "profile", None),
            static_modes=tuple(getattr(args, "static_modes", ())),
            static_agent=getattr(args, "static_agent", False),
        )