import argparse

from cli.static_parser import add_static_module
from cli.report_parser import add_report_module
from cli.enrichment_parser import add_enrichment_module



def create_common_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)

    common.add_argument("sample", help="Path to the sample to analyze")
    common.add_argument("--output", default="output", help="Output directory")
    common.add_argument("--format", choices=["json", "text"], default="json", help="Output format")
    
    return common



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AIM: AI Malware Analysis")

    subparsers = parser.add_subparsers(dest="phase", required=True)
    add_static_module(subparsers, create_common_parser())
    add_report_module(subparsers, create_common_parser())
    add_enrichment_module(subparsers, create_common_parser())

    return parser
