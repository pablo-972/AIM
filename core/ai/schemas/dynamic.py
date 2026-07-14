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
