import json
from json import JSONDecodeError
from typing import Any

from core.ai.schemas.inference import VALID_CONFIDENCE_LEVELS


DYNAMIC_INFERENCE_FINDING_SCHEMA = {
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
                    "properties": {
                        "category": {"type": "string"},
                        "summary": {"type": "string"},
                        "evidence": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "category",
                        "summary",
                        "evidence",
                    ],
                    "additionalProperties": False,
                },
            ],
        },
    },
    "required": [
        "thought",
        "confidence",
        "finding",
    ],
    "additionalProperties": False,
}


def parse_dynamic_inference_finding(content: str) -> dict[str, Any]:
    content = (content or "").strip()
    if not content:
        return _fallback_dynamic_inference("LLM returned an empty response.")

    try:
        result = json.loads(content)
    except (JSONDecodeError, TypeError):
        return _invalid_dynamic_inference()

    if not isinstance(result, dict):
        return _invalid_dynamic_inference()

    thought = result.get("thought")
    confidence = result.get("confidence")
    finding = result.get("finding")

    if not isinstance(thought, str):
        return _invalid_dynamic_inference()
    if confidence not in VALID_CONFIDENCE_LEVELS:
        return _invalid_dynamic_inference()
    if finding is not None and not _valid_dynamic_finding(finding):
        return _invalid_dynamic_inference()

    return {
        "thought": thought,
        "confidence": confidence,
        "finding": finding,
    }


def _valid_dynamic_finding(finding: Any) -> bool:
    if not isinstance(finding, dict):
        return False

    for field in ("category", "summary"):
        if not isinstance(finding.get(field), str):
            return False

    evidence = finding.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        return False

    for item in evidence:
        if not _valid_evidence_item(item):
            return False

    return True


def _valid_evidence_item(item: Any) -> bool:
    return isinstance(item, str) and bool(item.strip())


def _invalid_dynamic_inference() -> dict[str, Any]:
    return _fallback_dynamic_inference(
        "LLM returned an invalid response."
    )


def _fallback_dynamic_inference(reason: str) -> dict[str, Any]:
    return {
        "thought": reason,
        "confidence": "low",
        "finding": None,
    }
