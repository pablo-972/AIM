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
                {"type": "string"},
                {"type": "null"},
            ]
        },
        "evidence": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "type",
        "category",
        "summary",
        "confidence",
        "function",
        "address_range",
        "evidence",
    ],
    "additionalProperties": False,
}
