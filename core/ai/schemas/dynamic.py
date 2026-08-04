from core.ai.schemas.inference import (
    build_inference_finding_schema,
    parse_inference_finding,
)


DYNAMIC_FINDING_FIELDS = ("category", "explanation")

DYNAMIC_INFERENCE_FINDING_SCHEMA = build_inference_finding_schema(
    {
        "category": {"type": "string"},
        "explanation": {"type": "string"},
    }
)


def parse_dynamic_inference_finding(content: str) -> dict[str, object]:
    return parse_inference_finding(content, DYNAMIC_FINDING_FIELDS)
