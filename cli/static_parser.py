import argparse

from exceptions import CLIValidationError

STATIC_MODES = [
    "file",
    "hash",
    "metadata",
    "packer",
    "strings",
    "vt",
    "pe",
    "full",
]


def validate_static_args(args: argparse.Namespace) -> None:
    selected_modes = set(args.static_modes)

    if len(selected_modes) < 1:
        raise CLIValidationError("need at least one --mode")

    if "full" in selected_modes and len(selected_modes) > 1:
        raise CLIValidationError("'full' cannot be combined with other static modes")

    if args.static_ai and not {"strings", "full"} & selected_modes:
        raise CLIValidationError("--ai is only valid with 'strings' or 'full'")

    if args.profile != "local-static" and not args.static_ai:
        raise CLIValidationError("--profile can only be used together with --ai")


def add_static_module(
    subparsers: argparse._SubParsersAction,
    common: argparse.ArgumentParser,
) -> None:
    parser = subparsers.add_parser(
        "static",
        parents=[common],
        help="Run static analysis modules",
    )

    parser.add_argument(
        "--mode",
        dest="static_modes",
        action="append",
        choices=STATIC_MODES,
        default=[],
        help="Static analysis mode"
    )
    parser.add_argument(
        "--ai",
        dest="static_ai",
        action="store_true",
        help="Run AI analysis for extracted strings",
    )
    parser.add_argument(
        "--profile",
        choices=["local-static", "openai-static", "gemini-static"],
        default="local-static",
        help="Model profile to use with --ai",
    )

    parser.set_defaults(
        func="run_static",
        validator=validate_static_args,
    )
