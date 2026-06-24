import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from cli.base_parser import build_parser
from exceptions import CLIValidationError
from orchestrator.context import AnalysisContext


class FullParserTests(unittest.TestCase):
    def test_full_defaults(self) -> None:
        args = build_parser().parse_args(["full", "sample.exe"])

        self.assertEqual(args.phase, "full")
        self.assertEqual(args.func, "run_full")
        self.assertEqual(args.static_profile, "local-static")
        self.assertEqual(args.enrichment_profile, "local-enrichment")
        self.assertEqual(args.reversing_profile, "local-reversing")
        self.assertEqual(args.reversing_depth, 12)

    def test_full_accepts_independent_profiles(self) -> None:
        args = build_parser().parse_args(
            [
                "full",
                "sample.exe",
                "--static-profile",
                "gemini-static",
                "--enrichment-profile",
                "openai-enrichment",
                "--reversing-profile",
                "gemini-reversing",
                "--depth",
                "20",
            ]
        )

        self.assertEqual(args.static_profile, "gemini-static")
        self.assertEqual(args.enrichment_profile, "openai-enrichment")
        self.assertEqual(args.reversing_profile, "gemini-reversing")
        self.assertEqual(args.reversing_depth, 20)

    def test_full_rejects_non_positive_depth(self) -> None:
        args = build_parser().parse_args(
            ["full", "sample.exe", "--depth", "0"]
        )

        with self.assertRaises(CLIValidationError):
            args.validator(args)

    def test_full_profiles_are_normalized_into_context(self) -> None:
        with TemporaryDirectory() as directory:
            sample = Path(directory) / "sample.exe"
            sample.write_bytes(b"sample")
            args = build_parser().parse_args(
                [
                    "full",
                    str(sample),
                    "--static-profile",
                    "gemini-static",
                    "--enrichment-profile",
                    "openai-enrichment",
                    "--reversing-profile",
                    "gemini-reversing",
                ]
            )

            context = AnalysisContext.from_args(args)

        self.assertEqual(context.static_modes, [])
        self.assertEqual(context.reversing_modes, [])
        self.assertEqual(context.full_static_profile, "gemini-static")
        self.assertEqual(
            context.full_enrichment_profile,
            "openai-enrichment",
        )
        self.assertEqual(
            context.full_reversing_profile,
            "gemini-reversing",
        )


if __name__ == "__main__":
    unittest.main()
