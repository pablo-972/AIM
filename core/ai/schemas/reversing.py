REVERSING_TOOL_NAMES = [
    "string_xrefs",
    "import_xrefs",
    "function",
    "disassembly",
    "callers",
    "callees",
]

REVERSING_ACTION_NAMES = [
    "none",
    "finish",
    "seed_queue",
    *REVERSING_TOOL_NAMES,
]

REVERSING_TARGET_SCHEMA = {
    "type": "object",
    "properties": {
        "tool": {
            "type": "string",
            "enum": REVERSING_TOOL_NAMES,
        },
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
            "maxItems": 6,
            "items": REVERSING_TARGET_SCHEMA,
        },
    },
    "required": ["reasoning", "targets"],
    "additionalProperties": False,
}

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
                "ransom_note_generation",
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

REVERSING_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "thought": {"type": "string"},
        "confidence": {
            "type": "string",
            "enum": ["low", "medium", "high"],
        },
        "action": {
            "type": "string",
            "enum": REVERSING_ACTION_NAMES,
        },
        "parameters": {"type": "object"},
        "finding": {
            "anyOf": [
                REVERSING_FINDING_SCHEMA,
                {"type": "null"},
            ]
        },
    },
    "required": [
        "thought",
        "confidence",
        "action",
        "parameters",
        "finding",
    ],
    "additionalProperties": False,
}
