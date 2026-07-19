import argparse

from core.exceptions import CLIValidationError


REVERSING_TOOLS = [
    "info",
    "imports",
    "functions",
    "strings",
    "disasm",
    "xrefs",
    "string-xrefs",
    "import-xrefs",
    "callers",
    "callees",
    "full"
]
REVERSING_AI_PROFILES = [
    "local-reversing",
    "openai-reversing",
    "gemini-reversing",
]


def validate_reversing_args(args: argparse.Namespace) -> None:
    selected_tools = set(args.reversing_tools)

    if "full" in selected_tools and len(selected_tools) > 1:
        raise CLIValidationError("'full' cannot be combined with other reversing modes")

    if args.reversing_agent and selected_tools:
        raise CLIValidationError("--agent cannot be combined with manual reversing modes")

    if not args.reversing_agent and not selected_tools:
        raise CLIValidationError("Select at least one reversing mode or use --agent")

    if args.reversing_max_targets < 1:
        raise CLIValidationError("--max-targets must be greater than zero")

    if "disasm" in selected_tools and not args.function:
        raise CLIValidationError("reversing disasm requires --function")

    if "xrefs" in selected_tools and not args.function:
        raise CLIValidationError("reversing xrefs requires --function")
    
    if "string-xrefs" in selected_tools and not args.value:
        raise CLIValidationError("reversing string-xrefs requires --value")

    if "import-xrefs" in selected_tools and not args.value:
        raise CLIValidationError("reversing import-xrefs requires --value")

    if "callers" in selected_tools and not args.function:
        raise CLIValidationError("reversing callers requires --function")

    if "callees" in selected_tools and not args.function:
        raise CLIValidationError("reversing callees requires --function")


def add_reversing_module(
    subparsers: argparse._SubParsersAction,
    common: argparse.ArgumentParser,
) -> None:
    parser = subparsers.add_parser(
        "reversing",
        parents=[common],
        help="Reverse-engineering module",
    )

    parser.add_argument(
        "--tool",
        dest="reversing_tools",
        action="append",
        choices=REVERSING_TOOLS,
        default=[],
        help="Reverse tool to run. Can be used multiple times",
    )
    parser.add_argument(
        "--function",
        help="Function name or address",
    )
    parser.add_argument(
        "--value",
        help="String/import/address value used by xref-style modes",
    )
    parser.add_argument(
        "--agent",
        dest="reversing_agent",
        action="store_true",
        help="Run assisted reverse-engineering agent",
    )
    parser.add_argument(
        "--profile",
        choices=REVERSING_AI_PROFILES,
        default=None,
        help="Model profile for assisted reversing",
    )
    parser.add_argument(
        "--max-targets",
        dest="reversing_max_targets",
        type=int,
        default=12,
        help="Maximum number of unique targets executed by the reversing agent",
    )

    parser.set_defaults(
        func="run_reversing",
        validator=validate_reversing_args,
    )
