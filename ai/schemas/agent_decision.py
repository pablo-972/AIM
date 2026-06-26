AGENT_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "thought": {"type": "string"},
        "confidence": {
            "type": "string",
            "enum": ["low", "medium", "high"],
        },
        "action": {"type": "string"},
        "parameters": {
            "type": "object",
        },
    },
    "required": ["thought", "confidence", "action", "parameters"],
    "additionalProperties": False,
}


STATIC_AGENT_FINDING_SCHEMA = {
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
                    },
                    "required": ["category", "tone"],
                    "additionalProperties": False,
                },
            ],
        },
    },
    "required": ["thought", "confidence", "finding"],
    "additionalProperties": False,
}
