import argparse
from dataclasses import dataclass
from pathlib import Path

from core.exceptions import CLIValidationError
from core.utils.crypto import sha256_file


@dataclass(frozen=True)
class AnalysisContext:
    sample: Path
    sample_sha256: str
    output: Path
    output_format: str

    phase: str
    func: str | None
    profile: str | None

    static_tools: list[str]
    static_ai: bool

    dynamic_tools: list[str]
    dynamic_ai: bool
    dynamic_start: bool
    dynamic_stop: bool
    dynamic_filter: Path | None

    reversing_tools: list[str]
    value: str | None
    function: str | None
    reversing_agent: bool
    reversing_max_targets: int

    full_static_profile: str | None
    full_enrichment_profile: str | None
    full_reversing_profile: str | None

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "AnalysisContext":
        sample = Path(args.sample).expanduser().resolve()

        if not sample.exists():
            raise CLIValidationError(f"Sample does not exist: {sample}")
        if not sample.is_file():
            raise CLIValidationError(f"Sample is not a file: {sample}")

        sample_sha256 = sha256_file(sample)
        base_output = Path(args.output).expanduser().resolve()

        dynamic_filter = getattr(args, "dynamic_filter", None)
        dynamic_filter_path = None
        if dynamic_filter:
            dynamic_filter_path = Path(dynamic_filter).expanduser().resolve() 

        if dynamic_filter_path is not None:
            if not dynamic_filter_path.exists():
                raise CLIValidationError(f"Procmon filter does not exist: {dynamic_filter_path}")
            if not dynamic_filter_path.is_file():
                raise CLIValidationError(f"Procmon filter is not a file: {dynamic_filter_path}")

        return cls(
            sample=sample,
            sample_sha256=sample_sha256,
            output=base_output / sample_sha256,
            output_format=args.format,

            phase=args.phase,
            func=getattr(args, "func", None),
            profile=getattr(args, "profile", None),

            static_tools=getattr(args, "static_tools", []),
            static_ai=getattr(args, "static_ai", False),

            dynamic_tools=getattr(args, "dynamic_tools", []),
            dynamic_ai=getattr(args, "dynamic_ai", False),
            dynamic_start=getattr(args, "dynamic_start", False),
            dynamic_stop=getattr(args, "dynamic_stop", False),
            dynamic_filter=dynamic_filter_path,

            reversing_tools=getattr(args, "reversing_tools", []),
            value=getattr(args, "value", None),
            function=getattr(args, "function", None),
            reversing_agent=getattr(args, "reversing_agent", False),
            reversing_max_targets=getattr(args, "reversing_max_targets", 12),
            
            full_static_profile=getattr(args, "static_profile", None),
            full_enrichment_profile=getattr(args, "enrichment_profile", None),
            full_reversing_profile=getattr(args, "reversing_profile", None),
        )
