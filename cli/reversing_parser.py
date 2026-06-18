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
]


def validate_reversing_args(args: argparse.Namespace) -> None:
    if args.agent and args.reversing_modes:
        raise CLIValidationError("--agent cannot be combined with manual reverse modes")

    if not args.agent and not args.reversing_modes:
        raise CLIValidationError("Select at least one reverse mode or use --agent")

    if "disasm" in args.reversing_modes and not args.function:
        raise CLIValidationError("reverse disasm requires --function")

    if "xrefs" in args.reversing_modes and not args.value:
        raise CLIValidationError("reverse xrefs requires --value")
    
    if "string-xrefs" in args.reversing_modes and not args.value:
        raise CLIValidationError("reverse string-xrefs requires --value")

    if "callers" in args.reversing_modes and not args.function:
        raise CLIValidationError("reverse callers requires --function")

    if "callees" in args.reversing_modes and not args.function:
        raise CLIValidationError("reverse callees requires --function")


def add_reversing_module(subparsers: argparse._SubParsersAction, common: argparse.ArgumentParser) -> None:
    parser = subparsers.add_parser(
        "reversing",
        parents=[common],
        help="Reverse-engineering module",
    )

    parser.add_argument(
        "reversing_modes",
        nargs="*",
        choices=REVERSING_MODES,
        metavar="mode",
        help="Reverse modes to run",
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