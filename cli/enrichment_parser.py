import argparse


def add_enrichment_module(
    subparsers: argparse._SubParsersAction,
    common: argparse.ArgumentParser,
) -> None:
    parser = subparsers.add_parser(
        "enrichment",
        parents=[common],
        help="Generate enrichment data using an AI model",
    )

    parser.add_argument(
        "--profile",
        choices=["local-enrichment", "openai-enrichment", "gemini-enrichment"],
        default="local-enrichment",
        help="AI model profile",
    )

    parser.set_defaults(
        func="run_enrichment",
        validator=None,
    )
