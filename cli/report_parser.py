import argparse


def add_report_module(
    subparsers: argparse._SubParsersAction,
    common: argparse.ArgumentParser,
) -> None:
    parser = subparsers.add_parser(
        "report",
        parents=[common],
        help="Generate a report using an AI model",
    )

    parser.add_argument(
        "--profile",
        choices=["local-report", "openai-report", "gemini-report"],
        default="local-report",
        help="AI model profile",
    )

    parser.set_defaults(
        func="run_report",
        validator=None,
    )
    
   

