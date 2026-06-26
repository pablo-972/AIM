import json
from json import JSONDecodeError
from typing import Any

REQUIRED_AGENT_DECISION_KEYS = {
    "thought",
    "confidence",
    "action",
    "parameters",
}
REQUIRED_STATIC_INFERENCE_KEYS = {
    "thought",
    "confidence",
    "finding",
}
VALID_CONFIDENCE_LEVELS = {
    "low",
    "medium",
    "high",
}


def parse_json_object(
    content: str,
    fallback: dict[str, Any],
) -> dict[str, Any]:
    content = (content or "").strip()
    if not content:
        return dict(fallback)

    try:
        value = json.loads(content)
    except (JSONDecodeError, TypeError):
        return dict(fallback)

    return value if isinstance(value, dict) else dict(fallback)


def parse_agent_decision(content: str) -> dict[str, Any]:
    content = (content or "").strip()
    if not content:
        return _fallback_agent_decision("LLM returned an empty response.")

    try:
        decision = json.loads(content)
    except (JSONDecodeError, TypeError):
        return _fallback_agent_decision("LLM returned an invalid response.")

    if not isinstance(decision, dict):
        return _fallback_agent_decision("LLM returned an invalid response.")

    if not REQUIRED_AGENT_DECISION_KEYS.issubset(decision):
        return _fallback_agent_decision("LLM returned an invalid response.")

    if decision["confidence"] not in VALID_CONFIDENCE_LEVELS:
        return _fallback_agent_decision("LLM returned an invalid response.")

    if not isinstance(decision["parameters"], dict):
        return _fallback_agent_decision("LLM returned an invalid response.")

    return decision


def parse_static_inference_finding(content: str) -> dict[str, Any]:
    content = (content or "").strip()
    if not content:
        return _fallback_static_inference_finding("LLM returned an empty response.")

    try:
        decision = json.loads(content)
    except (JSONDecodeError, TypeError):
        return _fallback_static_inference_finding("LLM returned an invalid response.")

    if not isinstance(decision, dict):
        return _fallback_static_inference_finding("LLM returned an invalid response.")

    if not REQUIRED_STATIC_INFERENCE_KEYS.issubset(decision):
        return _fallback_static_inference_finding("LLM returned an invalid response.")

    if decision["confidence"] not in VALID_CONFIDENCE_LEVELS:
        return _fallback_static_inference_finding("LLM returned an invalid response.")

    finding = decision.get("finding")
    if finding is not None:
        if not isinstance(finding, dict):
            return _fallback_static_inference_finding("LLM returned an invalid response.")
        if not isinstance(finding.get("category"), str):
            return _fallback_static_inference_finding("LLM returned an invalid response.")
        if not isinstance(finding.get("tone"), str):
            return _fallback_static_inference_finding("LLM returned an invalid response.")

    return {
        "thought": decision.get("thought") if isinstance(decision.get("thought"), str) else "",
        "confidence": decision["confidence"],
        "action": "none",
        "parameters": {},
        "finding": finding,
    }


def _fallback_agent_decision(reason: str) -> dict[str, Any]:
    return {
        "thought": reason,
        "confidence": "low",
        "action": "none",
        "parameters": {},
    }


def _fallback_static_inference_finding(reason: str) -> dict[str, Any]:
    return {
        "thought": reason,
        "confidence": "low",
        "action": "none",
        "parameters": {},
        "finding": None,
    }
