import argparse

from core.exceptions import CLIValidationError


STATIC_TOOLS = (
    "file",
    "hash",
    "metadata",
    "packer",
    "strings",
    "vt",
    "pe",
    "full",
)
STATIC_AI_PROFILES = (
    "local-static", 
    "openai-static", 
    "gemini-static",
)
STATIC_AI_TOOLS = {
    "strings", 
    "full",
}


def validate_static_args(args: argparse.Namespace) -> None:
    selected_tools = set(args.static_tools)

    if not selected_tools:
        raise CLIValidationError("Select at least one static tool with --tool")

    if "full" in selected_tools and len(selected_tools) > 1:
        raise CLIValidationError("'full' cannot be combined with other static modes")

    if args.static_ai and selected_tools.isdisjoint(STATIC_AI_TOOLS):
        raise CLIValidationError("--ai is only valid with 'strings' or 'full'")

    if args.profile is not None and not args.static_ai:
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
        choices=STATIC_AI_PROFILES,
        default=None,
        help="Model profile to use with --ai",
    )

    parser.set_defaults(
        func="run_static",
        validator=validate_static_args,
    )
