import argparse

from cli.static_parser import add_static_module
from cli.report_parser import add_report_module
from cli.enrichment_parser import add_enrichment_module


def create_common_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument(
        "sample",
        help="Path to the sample to analyze",
    )
    parser.add_argument(
        "--output",
        default="output",
        help="Output directory",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format",
    )

    return parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aim", description="AIM: AI Malware Analysis")

    common = create_common_parser()
    subparsers = parser.add_subparsers(dest="phase", required=True, metavar="phase")

    add_static_module(subparsers, common)
    add_enrichment_module(subparsers, common)
    add_report_module(subparsers, common)

    return parser