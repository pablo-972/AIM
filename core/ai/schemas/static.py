from core.ai.schemas.inference import (
    build_inference_finding_schema,
    parse_inference_finding,
)


STATIC_FINDING_FIELDS = ("category", "tone")

STATIC_INFERENCE_FINDING_SCHEMA = build_inference_finding_schema(
    {
        "category": {"type": "string"},
        "tone": {"type": "string"},
    }
)


def parse_static_inference_finding(content: str) -> dict[str, object]:
    return parse_inference_finding(content, STATIC_FINDING_FIELDS)
