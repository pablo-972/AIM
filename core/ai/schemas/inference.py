import json
from json import JSONDecodeError
from typing import Any


REQUIRED_INFERENCE_KEYS = (
    "thought",
    "confidence",
    "finding",
)
VALID_CONFIDENCE_LEVELS = (
    "low",
    "medium",
    "high",
)


def build_inference_finding_schema(
    finding_properties: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "thought": {"type": "string"},
            "confidence": {
                "type": "string",
                "enum": list(VALID_CONFIDENCE_LEVELS),
            },
            "finding": {
                "anyOf": [
                    {"type": "null"},
                    {
                        "type": "object",
                        "properties": finding_properties,
                        "required": list(finding_properties),
                        "additionalProperties": False,
                    },
                ],
            },
        },
        "required": list(REQUIRED_INFERENCE_KEYS),
        "additionalProperties": False,
    }


def parse_inference_finding(
    content: str,
    required_finding_fields: tuple[str, ...],
) -> dict[str, Any]:
    content = (content or "").strip()
    if not content:
        return _fallback_inference_finding("LLM returned an empty response.")

    try:
        result = json.loads(content)
    except (JSONDecodeError, TypeError):
        return _invalid_inference_finding()

    if not isinstance(result, dict):
        return _invalid_inference_finding()
    if not all(key in result for key in REQUIRED_INFERENCE_KEYS):
        return _invalid_inference_finding()
    if result.get("confidence") not in VALID_CONFIDENCE_LEVELS:
        return _invalid_inference_finding()

    finding = result.get("finding")
    if finding is not None and not _valid_finding(finding, required_finding_fields):
        return _invalid_inference_finding()

    thought = result.get("thought")
    if not isinstance(thought, str):
        thought = "LLM returned a non-text thought."

    return {
        "thought": thought,
        "confidence": result["confidence"],
        "finding": finding,
    }


def _valid_finding(
    finding: Any,
    required_finding_fields: tuple[str, ...],
) -> bool:
    if not isinstance(finding, dict):
        return False

    for field in required_finding_fields:
        if not isinstance(finding.get(field), str):
            return False

    return True


def _invalid_inference_finding() -> dict[str, Any]:
    return _fallback_inference_finding(
        "LLM returned an invalid response."
    )


def _fallback_inference_finding(reason: str) -> dict[str, Any]:
    return {
        "thought": reason,
        "confidence": "low",
        "finding": None,
    }
