import argparse

from exceptions import CLIValidationError

REVERSING_MODES = [
    "info",
    "imports",
    "functions",
    "strings",
    "disasm",
    "xrefs",
    "string-xrefs",
    "callers",
    "callees",
    "full"
]


def validate_reversing_args(args: argparse.Namespace) -> None:
    selected_modes = set(args.reversing_modes)

    if "full" in selected_modes and len(selected_modes) > 1:
        raise CLIValidationError("'full' cannot be combined with other static modes")

    if args.reversing_agent and selected_modes:
        raise CLIValidationError("--agent cannot be combined with manual reverse modes")

    if not args.reversing_agent and not selected_modes:
        raise CLIValidationError("Select at least one reverse mode or use --agent")

    if "disasm" in selected_modes and not args.function:
        raise CLIValidationError("reverse disasm requires --function")

    if "xrefs" in selected_modes and not args.value:
        raise CLIValidationError("reverse xrefs requires --value")
    
    if "string-xrefs" in selected_modes and not args.value:
        raise CLIValidationError("reverse string-xrefs requires --value")

    if "callers" in selected_modes and not args.function:
        raise CLIValidationError("reverse callers requires --function")

    if "callees" in selected_modes and not args.function:
        raise CLIValidationError("reverse callees requires --function")


def add_reversing_module(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    common: argparse.ArgumentParser,
) -> None:
    parser = subparsers.add_parser(
        "reversing",
        parents=[common],
        help="Reverse-engineering module",
    )

    parser.add_argument(
        "--mode",
        dest="reversing_modes",
        action="append",
        choices=REVERSING_MODES,
        default=[],
        help="Reverse mode to run. Can be used multiple times",
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
        choices=["local-reverse", "openai-reverse", "gemini-reverse"],
        default=None,
        help="Model profile for assisted reversing",
    )

    parser.set_defaults(
        func="run_reversing",
        validator=validate_reversing_args,
    )
