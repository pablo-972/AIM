import json
from json import JSONDecodeError
from typing import Any


REQUIRED_DYNAMIC_INFERENCE_KEYS = {
    "thought",
    "confidence",
    "finding",
}
VALID_CONFIDENCE_LEVELS = {
    "low",
    "medium",
    "high",
}


DYNAMIC_INFERENCE_FINDING_SCHEMA = {
    "type": "object",
    "properties": {
        "thought": {"type": "string"},
        "confidence": {
            "type": "string",
            "enum": ["low", "medium", "high"],
        },
        "finding": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "tone": {"type": "string"},
                        "explanation": {"type": "string"},
                    },
                    "required": ["category", "tone", "explanation"],
                    "additionalProperties": False,
                },
            ],
        },
    },
    "required": ["thought", "confidence", "finding"],
    "additionalProperties": False,
}


def parse_dynamic_inference_finding(content: str) -> dict[str, Any]:
    content = (content or "").strip()
    if not content:
        return _fallback_inference_finding("LLM returned an empty response.")

    try:
        decision = json.loads(content)
    except (JSONDecodeError, TypeError):
        return _fallback_inference_finding("LLM returned an invalid response.")

    if not isinstance(decision, dict):
        return _fallback_inference_finding("LLM returned an invalid response.")

    if not REQUIRED_DYNAMIC_INFERENCE_KEYS.issubset(decision):
        return _fallback_inference_finding("LLM returned an invalid response.")

    if decision["confidence"] not in VALID_CONFIDENCE_LEVELS:
        return _fallback_inference_finding("LLM returned an invalid response.")

    finding = decision.get("finding")
    if finding is not None:
        if not isinstance(finding, dict):
            return _fallback_inference_finding("LLM returned an invalid response.")

        for key in {"category", "tone", "explanation"}:
            if not isinstance(finding.get(key), str):
                return _fallback_inference_finding("LLM returned an invalid response.")

    thought = decision.get("thought")
    if not isinstance(thought, str):
        thought = ""

    return {
        "thought": thought,
        "confidence": decision.get("confidence"),
        "finding": finding,
    }


def _fallback_inference_finding(reason: str) -> dict[str, Any]:
    return {
        "thought": reason,
        "confidence": "low",
        "finding": None,
    }
