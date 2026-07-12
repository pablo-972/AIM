import argparse

from exceptions import CLIValidationError


STATIC_PROFILES = [
    "local-static",
    "openai-static",
    "gemini-static",
]
ENRICHMENT_PROFILES = [
    "local-enrichment",
    "openai-enrichment",
    "gemini-enrichment",
]
REVERSING_PROFILES = [
    "local-reversing",
    "openai-reversing",
    "gemini-reversing",
]


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
        choices=STATIC_PROFILES,
        default="local-static",
        help="Model profile for static strings inference",
    )
    parser.add_argument(
        "--enrichment-profile",
        choices=ENRICHMENT_PROFILES,
        default="local-enrichment",
        help="Model profile for enrichment",
    )
    parser.add_argument(
        "--reversing-profile",
        choices=REVERSING_PROFILES,
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

    parser.set_defaults(
        func="run_full",
        validator=validate_full_args,
    )
