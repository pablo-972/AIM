from typing import Any

from core.ai.agents.reversing import ReversingAgent
from core.utils.logger import Logger


FALLBACK_ANALYSIS_ATTEMPTS = 2


class ReversingEvidenceAnalyzer:
    def __init__(
        self,
        agent: ReversingAgent,
        enrichment: str,
        available_tools: dict[str, Any],
    ) -> None:
        self.agent = agent
        self.enrichment = enrichment
        self.available_tools = available_tools

    def analyze_chunk(
        self,
        target: dict[str, Any],
        observation: dict[str, Any],
        chunk: Any,
        chunk_index: int,
        total_chunks: int,
        analysis_context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], str | None]:
        errors = []
        attempts = self._attempts()

        for index, attempt_data in enumerate(attempts):
            enrichment, label, attempt, total_attempts = attempt_data
            try:
                return self._request_analysis(
                    enrichment,
                    target,
                    observation,
                    chunk,
                    chunk_index,
                    total_chunks,
                    analysis_context,
                ), None
            except Exception as exc:
                errors.append(f"{label} attempt {attempt}: {exc}")
                next_attempt = self._next_attempt(attempts, index)

                if next_attempt is not None:
                    self._log_retry(target, chunk_index, next_attempt)

        error = "LLM analysis failed after retries: " + "; ".join(errors)
        
        Logger.error(
            f"Reversing agent failed for {target['tool']} "
            f"chunk {chunk_index}: {error}"
        )
        
        return self._failed_analysis(), error

    def _attempts(self) -> list[tuple[str, str, int, int]]:
        if self.enrichment:
            attempts = [(self.enrichment, "with enrichment", 1, 1)]
            attempts.extend(self._fallback_attempts())
            return attempts

        return self._fallback_attempts()

    def _fallback_attempts(self) -> list[tuple[str, str, int, int]]:
        return [
            ("", "without enrichment", attempt, FALLBACK_ANALYSIS_ATTEMPTS)
            for attempt in range(1, FALLBACK_ANALYSIS_ATTEMPTS + 1)
        ]

    def _next_attempt(
        self,
        attempts: list[tuple[str, str, int, int]],
        current_index: int,
    ) -> tuple[str, int, int] | None:
        next_index = current_index + 1
        if next_index >= len(attempts):
            return None

        _, label, attempt, total_attempts = attempts[next_index]
        return label, attempt, total_attempts

    def _log_retry(
        self,
        target: dict[str, Any],
        chunk_index: int,
        next_attempt: tuple[str, int, int],
    ) -> None:
        label, attempt, attempts = next_attempt

        Logger.warning(
            f"Retrying {target['tool']} chunk {chunk_index} "
            f"{label} ({attempt}/{attempts})"
        )

    def _request_analysis(
        self,
        enrichment: str,
        target: dict[str, Any],
        observation: dict[str, Any],
        chunk: Any,
        chunk_index: int,
        total_chunks: int,
        analysis_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return self.agent.analyze_evidence(
            enrichment=enrichment,
            target=target,
            observation=observation,
            chunk=chunk,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            available_tools=self.available_tools,
            analysis_context=analysis_context,
        )

    def _failed_analysis(self) -> dict[str, Any]:
        return {
            "summary": "LLM decision failed.",
            "thinking": [],
            "confidence": "low",
            "tool_calls": [],
            "finished": False,
            "finding": None,
        }
