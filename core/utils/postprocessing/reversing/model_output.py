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
        lowered = self._prepare_finding_text(text).lower()
        if lowered.startswith("{"):
            if '"evidence"' in lowered:
                return True
        if lowered.startswith("["):
            if '"finding"' in lowered or '"evidence"' in lowered:
                return True

        for prefix in FINDING_TEXT_PREFIXES:
            if lowered.startswith(prefix):
                return True

        return False

    def _prepare_finding_text(self, text: str) -> str:
        prepared = self._remove_leading_list_marker(text)
        prepared = self._remove_code_fence(prepared)
        prepared = self._remove_json_language_label(prepared)
        return prepared.strip()

    def _remove_leading_list_marker(self, text: str) -> str:
        stripped = text.lstrip()
        for marker in ("- ", "* "):
            if stripped.startswith(marker):
                return stripped[len(marker):].lstrip()

        return stripped

    def _remove_code_fence(self, text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            return "\n".join(lines).strip()

        if stripped.startswith("`"):
            stripped = stripped[1:]
            if stripped.endswith("`"):
                stripped = stripped[:-1]

        return stripped.strip()

    def _remove_json_language_label(self, text: str) -> str:
        stripped = text.lstrip()
        first_line, separator, rest = stripped.partition("\n")
        if separator and first_line.strip().lower() == "json":
            return rest.strip()

        return stripped

    def _extract_finding(
        self,
        text: str,
    ) -> dict[str, Any] | None:
        decoded = self._decode_first_json_value(text)
        return self._finding_from_decoded(decoded)

    def _finding_from_decoded(
        self,
        decoded: Any,
    ) -> dict[str, Any] | None:
        if isinstance(decoded, list):
            for item in decoded:
                finding = self._finding_from_decoded(item)
                if finding is not None:
                    return finding

            return None

        if not isinstance(decoded, dict):
            return None

        nested_finding = decoded.get("finding")
        if isinstance(nested_finding, dict):
            return nested_finding

        if self._looks_like_finding(decoded):
            return decoded

        return None

    def _decode_first_json_value(
        self,
        text: str,
    ) -> Any:
        prepared = self._prepare_finding_text(text)
        start = self._json_start(prepared)
        if start < 0:
            return None

        json_text = prepared[start:]

        try:
            decoded, _ = json.JSONDecoder().raw_decode(json_text)
        except json.JSONDecodeError:
            return None

        return decoded

    def _json_start(self, text: str) -> int:
        starts = [
            position
            for position in (text.find("{"), text.find("["))
            if position >= 0
        ]
        if not starts:
            return -1

        return min(starts)

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
