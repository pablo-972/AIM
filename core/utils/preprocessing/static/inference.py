from typing import Any

from core.utils.artifacts.extractor import JsonExtractor


def prepare_static_inference_sources(
    static_inference_data: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    if not static_inference_data:
        return []

    extractor = JsonExtractor(static_inference_data)
    findings = extractor.get_static_inference_findings()
    
    if not findings:
        return []

    return [
        (
            f"static_strings_inference.findings.{index}",
            {
                "confidence": finding.get("confidence"),
                "text": finding.get("text"),
                "category": finding.get("category"),
                "tone": finding.get("tone"),
            },
        )
        for index, finding in enumerate(findings, start=1)
    ]
