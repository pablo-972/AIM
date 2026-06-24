from dataclasses import dataclass
from typing import Any

from config import ENRICHMENT_FILENAME
from utils.io.text import read_text
from utils.logger import Logger
from utils.artifacts.documents import (
    EMPTY_DOCUMENT_BODY,
    ENRICHMENT_TITLE,
    MarkdownDocument,
)
from orchestrator.context import AnalysisContext
from tools.reversing.analyzers.reconnaissance import collect_reconnaissance
from ai.agents.reversing import ReversingAgent
from ai.runtime.reversing.targets import ReversingTargetQueue


@dataclass(frozen=True)
class ReversingInitialization:
    enrichment: str
    seed: dict[str, Any]
    targets: list[dict[str, Any]]
    source: str
    seed_error: str | None
    input_source: str

    def seed_decision(self) -> dict[str, Any]:
        first_target = (
            self.targets[0]
            if self.targets and isinstance(self.targets[0], dict)
            else None
        )
        return {
            "thought": str(self.seed.get("reasoning") or ""),
            "confidence": "medium" if first_target else "low",
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
        targets = (
            raw_targets[:6]
            if isinstance(raw_targets, list) and raw_targets
            else []
        )
        source = "seed"
        if not targets and not enrichment:
            targets = self.targets.fallback_targets(reconnaissance)
            seed = {
                "reasoning": "Using deterministic reconnaissance fallback.",
                "targets": targets,
            }
            source = "fallback"

        return seed, targets, source, seed_error
