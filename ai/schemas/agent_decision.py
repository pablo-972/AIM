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



