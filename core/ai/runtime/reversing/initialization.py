from dataclasses import dataclass
from typing import Any

from config import ENRICHMENT_FILENAME
from core.utils.io.text import read_text
from core.utils.logger import Logger
from core.utils.artifacts.documents import (
    EMPTY_DOCUMENT_BODY,
    ENRICHMENT_TITLE,
    MarkdownDocument,
)
from core.orchestrator.context import AnalysisContext
from core.tools.reversing.analyzers.reconnaissance import collect_reconnaissance
from core.ai.agents.reversing import ReversingAgent
from core.ai.runtime.reversing.targets import ReversingTargetQueue


@dataclass(frozen=True)
class ReversingInitialization:
    enrichment: str
    seed: dict[str, Any]
    targets: list[dict[str, Any]]
    source: str
    seed_error: str | None
    input_source: str

def seed_decision(self) -> dict[str, Any]:
    first_target = None
    if self.targets and isinstance(self.targets[0], dict):
        first_target = self.targets[0]

    confidence = "medium" if first_target else "low"
    thought = str(self.seed.get("reasoning") or "")

    return {
        "thought": thought,
        "confidence": confidence,
        "action": "seed_queue",
        "parameters": {},
    }



class ReversingInvestigationInitializer:
    def __init__(
        self,
        context: AnalysisContext,
        targets: ReversingTargetQueue,
        available_tools: dict[str, Any],
    ) -> None:
        self.context = context
        self.targets = targets
        self.available_tools = available_tools

    def initialize(self, agent: ReversingAgent) -> ReversingInitialization:
        enrichment = self._load_enrichment()
        reconnaissance = {}
        if not enrichment:
            reconnaissance = collect_reconnaissance(str(self.context.sample))

        seed, targets, source, seed_error = self._create_targets(
            agent,
            enrichment,
            reconnaissance,
        )

        if not targets:
            if not reconnaissance:
                reconnaissance = collect_reconnaissance(str(self.context.sample))
                
            targets = self.targets.fallback_targets(reconnaissance)
            if targets:
                seed = {
                    "reasoning": self._fallback_reason(seed_error),
                    "targets": targets,
                }
                source = "fallback"

        return ReversingInitialization(
            enrichment=enrichment,
            seed=seed,
            targets=targets,
            source=source,
            seed_error=seed_error,
            input_source="enrichment" if enrichment else "reconnaissance",
        )

    def _load_enrichment(self) -> str:
        path = self.context.output / ENRICHMENT_FILENAME
        document = MarkdownDocument(path, ENRICHMENT_TITLE)
        content = document.sanitize(read_text(path))
        if not content:
            return ""

        body = document.extract_body(content)
        return "" if body == EMPTY_DOCUMENT_BODY else body

    def _create_targets(
        self,
        agent: ReversingAgent,
        enrichment: str,
        reconnaissance: dict[str, Any],
    ) -> tuple[dict[str, Any], list[dict[str, Any]], str, str | None]:
        seed_error = None
        try:
            seed = agent.create_initial_targets(
                enrichment=enrichment,
                reconnaissance=reconnaissance,
                available_tools=self.available_tools,
            )
        except Exception as exc:
            seed_error = str(exc)
            Logger.error(f"Reversing seed decision failed: {exc}")
            seed = {
                "reasoning": "LLM decision failed.",
                "targets": [],
            }

        raw_targets = seed.get("targets")
        targets = self.targets.valid_targets(raw_targets)[:6]
        if isinstance(raw_targets, list) and raw_targets and not targets:
            seed_error = self._append_error(
                seed_error,
                "Seed returned no valid reversing targets.",
            )

        source = "seed"

        return seed, targets, source, seed_error

    def _fallback_reason(self, seed_error: str | None) -> str:
        reason = "Using deterministic reconnaissance fallback."
        if seed_error:
            return f"{reason} Seed error: {seed_error}"

        return reason

    def _append_error(
        self,
        current_error: str | None,
        message: str,
    ) -> str:
        if current_error:
            return f"{current_error}; {message}"

        return message
