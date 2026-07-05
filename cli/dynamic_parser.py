import argparse

from exceptions import CLIValidationError

DYNAMIC_TOOLS = [
    "autoruns",
    "regshot",
    "full",
]


def validate_dynamic_args(args: argparse.Namespace) -> None:
    selected_tools = set(args.dynamic_tools)
    machine_action = args.dynamic_start or args.dynamic_stop

    if args.dynamic_start and args.dynamic_stop:
        raise CLIValidationError("--start and --stop cannot be used together")

    if machine_action and selected_tools:
        raise CLIValidationError("--start/--stop cannot be combined with dynamic tools")

    if not machine_action and len(selected_tools) < 1:
        raise CLIValidationError("Select at least one dynamic tool with --tool")

    if "full" in selected_tools and len(selected_tools) > 1:
        raise CLIValidationError("'full' cannot be combined with other dynamic tools")

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
    parser.add_argument(
        "--start",
        dest="dynamic_start",
        action="store_true",
        help="Restore the victim VM snapshot and start the configured VMs",
    )
    parser.add_argument(
        "--stop",
        dest="dynamic_stop",
        action="store_true",
        help="Stop the configured VMs",
    )
    
    parser.set_defaults(
        func="run_dynamic",
        validator=validate_dynamic_args,
    )
