import json
from json import JSONDecodeError
from typing import Any


REPORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "report_markdown": {
            "type": "string",
            "description": "Complete malware analysis report formatted as Markdown.",
        },
        "assessment": {
            "type": "object",
            "properties": {
                "is_malware": {
                    "type": "boolean",
                },
                "malware_confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                },
                "family": {
                    "type": ["string", "null"],
                },
                "family_confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                },
                "categories": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                },
                "summary_reason": {
                    "type": "string",
                },
            },
            "required": [
                "is_malware",
                "malware_confidence",
                "family",
                "family_confidence",
                "categories",
                "summary_reason",
            ],
            "additionalProperties": False,
        },
    },
    "required": [
        "report_markdown",
        "assessment",
    ],
    "additionalProperties": False,
}


def parse_report_result(content: str) -> dict[str, Any]:
    content = sanitize_json_response(content)

    try:
        result = json.loads(content)
    except (JSONDecodeError, TypeError) as exc:
        raise ValueError("Report response is not valid JSON") from exc

    if not isinstance(result, dict):
        raise ValueError("Report response must be a JSON object")

    required_keys = {"report_markdown", "assessment"}
    missing_keys = required_keys - set(result)

    if missing_keys:
        missing = ", ".join(sorted(missing_keys))
        raise ValueError(f"Report response is missing required fields: {missing}")

    extra_keys = set(result) - required_keys
    if extra_keys:
        extra = ", ".join(sorted(extra_keys))
        raise ValueError(f"Report response contains unsupported fields: {extra}")

    report_markdown = result.get("report_markdown")
    if not isinstance(report_markdown, str) or not report_markdown.strip():
        raise ValueError("report_markdown must be a non-empty string")

    assessment = result.get("assessment")
    if not isinstance(assessment, dict):
        raise ValueError("assessment must be a JSON object")

    validate_assessment(assessment)

    return {
        "report_markdown": report_markdown,
        "assessment": assessment,
    }


def sanitize_json_response(content: str) -> str:
    content = (content or "").strip()

    if not content.startswith("```"):
        return content

    lines = content.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]

    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    return "\n".join(lines).strip()


def validate_assessment(assessment: dict[str, Any]) -> None:
    required_keys = {
        "is_malware",
        "malware_confidence",
        "family",
        "family_confidence",
        "categories",
        "summary_reason",
    }

    missing_keys = required_keys - set(assessment)
    if missing_keys:
        missing = ", ".join(sorted(missing_keys))
        raise ValueError(f"assessment is missing required fields: {missing}")

    extra_keys = set(assessment) - required_keys
    if extra_keys:
        extra = ", ".join(sorted(extra_keys))
        raise ValueError(f"assessment contains unsupported fields: {extra}")

    if not isinstance(assessment["is_malware"], bool):
        raise ValueError("assessment.is_malware must be a boolean")

    _validate_confidence(
        assessment["malware_confidence"],
        "assessment.malware_confidence",
    )
    _validate_confidence(
        assessment["family_confidence"],
        "assessment.family_confidence",
    )

    family = assessment["family"]
    if family is not None and not isinstance(family, str):
        raise ValueError("assessment.family must be a string or null")

    categories = assessment["categories"]
    if not isinstance(categories, list):
        raise ValueError("assessment.categories must be a list")

    for category in categories:
        if not isinstance(category, str):
            raise ValueError("assessment.categories must contain only strings")

    summary_reason = assessment["summary_reason"]
    if not isinstance(summary_reason, str) or not summary_reason.strip():
        raise ValueError("assessment.summary_reason must be a non-empty string")


def _validate_confidence(value: Any, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a number")

    if value < 0 or value > 1:
        raise ValueError(f"{field_name} must be between 0 and 1")
