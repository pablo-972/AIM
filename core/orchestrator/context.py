import argparse
from pathlib import Path
from dataclasses import dataclass, replace

from config import DEFAULT_REVERSING_MAX_TARGETS
from core.exceptions import CLIValidationError
from core.utils.crypto import sha256_file


@dataclass(frozen=True)
class StaticOptions:
    tools: tuple[str, ...]
    ai: bool


@dataclass(frozen=True)
class DynamicOptions:
    tools: tuple[str, ...]
    ai: bool
    start: bool
    stop: bool
    filter: Path | None


@dataclass(frozen=True)
class ReversingOptions:
    tools: tuple[str, ...]
    value: str | None
    address: str | None
    function: str | None
    section: str | None
    agent: bool
    max_targets: int


@dataclass(frozen=True)
class FullOptions:
    static_profile: str | None
    dynamic_profile: str | None
    enrichment_profile: str | None
    reversing_profile: str | None
    report_profile: str | None


@dataclass(frozen=True)
class AnalysisContext:
    sample: Path
    sample_filename: str
    sample_sha256: str
    output: Path
    output_format: str

    phase: str
    func: str | None
    profile: str | None

    static: StaticOptions
    dynamic: DynamicOptions
    reversing: ReversingOptions
    full: FullOptions

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "AnalysisContext":
        sample = _resolve_file(args.sample, label="Sample")
        sample_sha256 = sha256_file(sample)
        sample_filename = getattr(args, "sample_filename", None) or sample.name

        base_output = Path(args.output).expanduser().resolve()

        dynamic_filter = getattr(args, "dynamic_filter", None)
        dynamic_filter_path = None
        if dynamic_filter:
            dynamic_filter_path = _resolve_file(dynamic_filter, label="Procmon filter")

        reversing_max_targets = getattr(args, "reversing_max_targets", None)
            
        return cls(
            sample=sample,
            sample_filename=str(sample_filename),
            sample_sha256=sample_sha256,
            output=base_output / sample_sha256,
            output_format=args.format,

            phase=args.phase,
            func=args.func,
            profile=getattr(args, "profile", None),

            static=StaticOptions(
                tools=tuple(getattr(args, "static_tools", [])),
                ai=getattr(args, "static_ai", False),
            ),

            dynamic=DynamicOptions(
                tools=tuple(getattr(args, "dynamic_tools", [])),
                ai=getattr(args, "dynamic_ai", False),
                start=getattr(args, "dynamic_start", False),
                stop=getattr(args, "dynamic_stop", False),
                filter=dynamic_filter_path,
            ),

            reversing=ReversingOptions(
                tools=tuple(getattr(args, "reversing_tools", [])),
                value=getattr(args, "value", None),
                function=getattr(args, "function", None),
                section=getattr(args, "section", None),
                address=getattr(args, "address", None),
                agent=getattr(args, "reversing_agent", False),
                max_targets=(
                    DEFAULT_REVERSING_MAX_TARGETS
                    if reversing_max_targets is None
                    else reversing_max_targets
                ),
            ),
            
            full=FullOptions(
                static_profile=getattr(args, "static_profile", None),
                dynamic_profile=getattr(args, "dynamic_profile", None),
                enrichment_profile=getattr(args, "enrichment_profile", None),
                reversing_profile=getattr(args, "reversing_profile", None),
                report_profile=getattr(args, "report_profile", None),
            ),
        )

    def for_full_static(self) -> "AnalysisContext":
        return replace(
            self,
            phase="static",
            func="run_static",
            static=replace(
                self.static,
                tools=("full",),
                ai=True,
            ),
            profile=self.full.static_profile,
        )

    def for_full_dynamic(self) -> "AnalysisContext":
        return replace(
            self,
            phase="dynamic",
            func="run_dynamic",
            dynamic=replace(
                self.dynamic,
                tools=("full",),
                ai=True,
                start=False,
                stop=False,
            ),
            profile=self.full.dynamic_profile,
        )

    def for_full_enrichment(self) -> "AnalysisContext":
        return replace(
            self,
            phase="enrichment",
            func="run_enrichment",
            profile=self.full.enrichment_profile,
        )

    def for_full_reverse_info(self) -> "AnalysisContext":
        return replace(
            self,
            phase="reversing",
            func="run_reversing",
            reversing=replace(
                self.reversing,
                tools=("full",),
                agent=False,
            ),
            profile=None,
        )

    def for_full_reverse_agent(self) -> "AnalysisContext":
        return replace(
            self,
            phase="reversing",
            func="run_reversing",
            reversing=replace(
                self.reversing,
                tools=(),
                agent=True,
            ),
            profile=self.full.reversing_profile,
        )

    def for_full_report(self) -> "AnalysisContext":
        return replace(
            self,
            phase="report",
            func="run_report",
            profile=self.full.report_profile,
        )


def _resolve_file(path: str | Path, *, label: str) -> Path:
    resolved = Path(path).expanduser().resolve()

    if not resolved.exists():
        raise CLIValidationError(f"{label} does not exist: {resolved}")
    if not resolved.is_file():
        raise CLIValidationError(f"{label} is not a file: {resolved}")

    return resolved
