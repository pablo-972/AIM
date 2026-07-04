import argparse

from exceptions import CLIValidationError

DYNAMIC_TOOLS = [
    "autoruns",
    "regshot",
    "full",
]


def validate_dynamic_args(args: argparse.Namespace) -> None:
    selected_tools = set(args.dynamic_tools)

    if len(selected_tools) < 1:
        raise CLIValidationError("Select at least one static mode with --mode")

    if "full" in selected_tools and len(selected_tools) > 1:
        raise CLIValidationError("'full' cannot be combined with other static modes")

    if args.profile != "local-dynamic" and not args.dynamic_ai:
        raise CLIValidationError("--profile can only be used together with --ai")


def add_dynamic_module(
    subparsers: argparse._SubParsersAction,
    common: argparse.ArgumentParser,
) -> None:
    parser = subparsers.add_parser(
        "dynamic",
        parents=[common],
        help="Run dynamic analysis modules",
    )

    parser.add_argument(
        "--tool",
        dest="dynamic_tools",
        action="append",
        choices=DYNAMIC_TOOLS,
        default=[],
        help="Dynamic analysis tool"
    )
    parser.add_argument(
        "--ai",
        dest="dynamic_ai",
        action="store_true",
        help="Run AI analysis for diffing",
    )
    parser.add_argument(
        "--profile",
        choices=["local-dynamic", "openai-dynamic", "gemini-dynamic"],
        default="local-dynamic",
        help="Model profile to use with --ai",
    )

    parser.set_defaults(
        func="run_dynamic",
        validator=validate_dynamic_args,
    )