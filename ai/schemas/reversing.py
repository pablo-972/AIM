REVERSING_TARGET_SCHEMA = {
    "type": "object",
    "properties": {
        "tool": {"type": "string"},
        "parameters": {"type": "object"},
        "priority": {
            "type": "integer",
            "minimum": 1,
            "maximum": 100,
        },
        "reason": {"type": "string"},
    },
    "required": ["tool", "parameters", "priority", "reason"],
    "additionalProperties": False,
}


REVERSING_SEED_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string"},
        "targets": {
            "type": "array",
            "items": REVERSING_TARGET_SCHEMA,
        },
    },
    "required": ["reasoning", "targets"],
    "additionalProperties": False,
}


REVERSING_FINDING_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string"},
        "summary": {"type": "string"},
        "confidence": {
            "type": "string",
            "enum": ["low", "medium", "high"],
        },
        "evidence": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["type", "summary", "confidence", "evidence"],
    "additionalProperties": False,
}


REVERSING_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "relevant": {"type": "boolean"},
        "thought": {"type": "string"},
        "confidence": {
            "type": "string",
            "enum": ["low", "medium", "high"],
        },
        "finding": {
            "anyOf": [
                REVERSING_FINDING_SCHEMA,
                {"type": "null"},
            ]
        },
        "next_targets": {
            "type": "array",
            "items": REVERSING_TARGET_SCHEMA,
        },
        "finish": {"type": "boolean"},
    },
    "required": [
        "relevant",
        "thought",
        "confidence",
        "finding",
        "next_targets",
        "finish",
    ],
    "additionalProperties": False,
}
