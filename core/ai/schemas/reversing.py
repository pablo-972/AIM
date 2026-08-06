ADDRESS_RANGE_SCHEMA = {
    "type": "object",
    "properties": {
        "start": {
            "anyOf": [
                {"type": "string"},
                {"type": "null"},
            ]
        },
        "end": {
            "anyOf": [
                {"type": "string"},
                {"type": "null"},
            ]
        },
    },
    "required": ["start", "end"],
    "additionalProperties": False,
}

REVERSING_FINDING_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string"},
        "category": {
            "type": "string",
            "enum": [
                "file_encryption",
                "crypto",
                "defense_evasion",
                "network",
                "persistence",
                "privilege_escalation",
                "api_resolution",
                "anti_analysis",
                "unknown",
            ],
        },
        "summary": {"type": "string"},
        "confidence": {
            "type": "string",
            "enum": ["low", "medium", "high"],
        },
        "function": {
            "anyOf": [
                {"type": "string"},
                {"type": "null"},
            ]
        },
        "address_range": {
            "anyOf": [
                ADDRESS_RANGE_SCHEMA,
                {"type": "null"},
            ]
        },
        "evidence": {
            "type": "array",
            "items": {"type": "string"},
        },
        "reason": {"type": "string"},
    },
    "required": [
        "type",
        "category",
        "summary",
        "confidence",
        "function",
        "address_range",
        "evidence",
        "reason",
    ],
    "additionalProperties": False,
}
