import json
from json import JSONDecodeError


REQUIRED_AGENT_DECISION_KEYS = {
    "thought",
    "confidence",
    "action",
    "parameters",
}

VALID_CONFIDENCE_LEVELS = {
    "low",
    "medium",
    "high",
}


def _fallback_agent_decision(reason: str) -> dict:
    return {
        "thought": reason,
        "confidence": "low",
        "action": "none",
        "parameters": {},
    }


def parse_agent_decision(content: str) -> dict:
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
