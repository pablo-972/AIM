import argparse

from core.exceptions import CLIValidationError
from cli.static_parser import STATIC_AI_PROFILES
from cli.dynamic_parser import DYNAMIC_AI_PROFILES
from cli.enrichment_parser import ENRICHMENT_AI_PROFILES
from cli.reversing_parser import REVERSING_AI_PROFILES
from cli.report_parser import REPORT_AI_PROFILES


def validate_full_args(args: argparse.Namespace) -> None:
    if args.reversing_max_targets < 1:
        raise CLIValidationError("--max-targets must be greater than zero")


def add_full_module(
    subparsers: argparse._SubParsersAction,
    common: argparse.ArgumentParser,
) -> None:
    parser = subparsers.add_parser(
        "full",
        parents=[common],
        help="Run the complete static, dynamic, enrichment, reversing, and report pipeline",
    )

    parser.add_argument(
        "--static-profile",
        choices=STATIC_AI_PROFILES,
        default="local-static",
        help="Model profile for static strings inference",
    )
    parser.add_argument(
        "--dynamic-profile",
        choices=DYNAMIC_AI_PROFILES,
        default="local-dynamic",
        help="Model profile for dynamic inference",
    )
    parser.add_argument(
        "--enrichment-profile",
        choices=ENRICHMENT_AI_PROFILES,
        default="local-enrichment",
        help="Model profile for enrichment",
    )
    parser.add_argument(
        "--reversing-profile",
        choices=REVERSING_AI_PROFILES,
        default="local-reversing",
        help="Model profile for the reversing agent",
    )
    parser.add_argument(
        "--max-targets",
        dest="reversing_max_targets",
        type=int,
        default=12,
        help="Maximum number of unique targets executed by the reversing agent",
    )
    parser.add_argument(
        "--report-profile",
        choices=REPORT_AI_PROFILES,
        default="local-report",
        help="Model profile for report generation",
    )

    parser.set_defaults(
        func="run_full",
        validator=validate_full_args,
    )
