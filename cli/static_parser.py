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

    if "full" in selected_modes and len(selected_modes) > 1:
        raise CLIValidationError("'full' cannot be combined with other static modes")

    if args.static_agent and not {"strings", "full"} & selected_modes:
        raise CLIValidationError("--agent is only valid with 'strings' or 'full'")

    if args.profile != "local-static" and not args.static_agent:
        raise CLIValidationError("--profile can only be used together with --agent")


def add_static_module(subparsers: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    parser = subparsers.add_parser(
        "static",
        parents=[common],
        help="Run static analysis modules",
    )

    parser.add_argument(
        "static_modes",
        nargs="+",
        choices=STATIC_MODES,
        metavar="mode",
        help="Static modes to run",
    )
    parser.add_argument(
        "--agent",
        dest="static_agent",
        action="store_true",
        help="Run AI analysis for extracted strings",
    )
    parser.add_argument(
        "--profile",
        choices=["local-static", "openai-static", "gemini-static"],
        default="local-static",
        help="Model profile to use with --agent",
    )

    parser.set_defaults(
        func="run_static",
        validator=validate_static_args,
    )