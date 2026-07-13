import argparse

from core.exceptions import CLIValidationError

STATIC_TOOLS = [
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
    selected_tools = set(args.static_tools)

    if len(selected_tools) < 1:
        raise CLIValidationError("Select at least one static mode with --mode")

    if "full" in selected_tools and len(selected_tools) > 1:
        raise CLIValidationError("'full' cannot be combined with other static modes")

    if args.static_ai and not {"strings", "full"} & selected_tools:
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
        "--tool",
        dest="static_tools",
        action="append",
        choices=STATIC_TOOLS,
        default=[],
        help="Static analysis tool"
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
