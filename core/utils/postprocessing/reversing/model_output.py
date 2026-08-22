import json
from typing import Any


FINDING_TEXT_PREFIXES = (
    "record finding",
    "record_finding",
    "finding",
)
FALLBACK_THOUGHT = "The model emitted a finding as text; it was normalized."
UNPARSED_FALLBACK_THOUGHT = (
    "The model emitted a finding as text, but it could not be normalized."
)


class ReversingModelOutputCleaner:
    def clean(self, analysis: Any) -> dict[str, Any]:
        if not isinstance(analysis, dict):
            return {}

        cleaned = dict(analysis)

        thought = cleaned.get("thought")
        if not isinstance(thought, str):
            return cleaned

        finding_text = thought.strip()

        if not self._looks_like_finding_text(finding_text):
            return cleaned

        existing_finding = cleaned.get("finding")
        if isinstance(existing_finding, dict):
            cleaned["thought"] = UNPARSED_FALLBACK_THOUGHT
            return cleaned

        recovered_finding = self._extract_finding(finding_text)

        if recovered_finding is None:
            cleaned["thought"] = UNPARSED_FALLBACK_THOUGHT
            return cleaned

        cleaned["finding"] = recovered_finding
        cleaned["thought"] = FALLBACK_THOUGHT

        return cleaned

    def _looks_like_finding_text(self, text: str) -> bool:
        lowered = text.lower().lstrip()
        if lowered.startswith("{"):
            if '"evidence"' in lowered:
                return True

        for prefix in FINDING_TEXT_PREFIXES:
            if lowered.startswith(prefix):
                return True

        return False

    def _extract_finding(
        self,
        text: str,
    ) -> dict[str, Any] | None:
        decoded = self._decode_first_json_object(text)
        if not isinstance(decoded, dict):
            return None

        nested_finding = decoded.get("finding")
        if isinstance(nested_finding, dict):
            return nested_finding

        if self._looks_like_finding(decoded):
            return decoded

        return None

    def _decode_first_json_object(
        self,
        text: str,
    ) -> Any:
        start = text.find("{")
        if start < 0:
            return None

        json_text = text[start:]

        try:
            decoded, _ = json.JSONDecoder().raw_decode(json_text)
        except json.JSONDecodeError:
            return None

        return decoded

    def _looks_like_finding(
        self,
        value: dict[str, Any],
    ) -> bool:
        summary = value.get("summary")
        if not isinstance(summary, str):
            return False

        confidence = value.get("confidence")
        if not isinstance(confidence, str):
            return False

        evidence = value.get("evidence")
        if not isinstance(evidence, list):
            return False

        return True
