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
from core.tools.reversing.analyzers.metadata import entrypoints
from core.ai.agents.reversing import ReversingAgent
from core.ai.runtime.reversing.targets import ReversingTargetQueue
from core.utils.address import parse_address


ENTRY_POINT_BASE_PRIORITY = 55


@dataclass(frozen=True)
class ReversingInitialization:
    enrichment: str
    seed: dict[str, Any]
    targets: list[dict[str, Any]]
    source: str
    seed_error: str | None
    input_source: str
    baseline_targets: list[dict[str, Any]]

    def seed_decision(self) -> dict[str, Any]:
        first_target = None
        if self.targets and isinstance(self.targets[0], dict):
            first_target = self.targets[0]

        confidence = "medium" if first_target else "low"
        thought = str(self.seed.get("thought") or "")

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
        seed, targets, source, seed_error = self._create_targets(
            agent,
            enrichment,
        )

        baseline_targets = self._entrypoint_baseline_targets()

        return ReversingInitialization(
            enrichment=enrichment,
            seed=seed,
            targets=targets,
            source=source,
            seed_error=seed_error,
            input_source="enrichment" if enrichment else "no_enrichment",
            baseline_targets=baseline_targets,
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
    ) -> tuple[dict[str, Any], list[dict[str, Any]], str, str | None]:
        seed_error = None
        try:
            seed = agent.create_initial_targets(
                enrichment=enrichment,
                available_tools=self.available_tools,
            )
        except Exception as exc:
            seed_error = str(exc)
            Logger.error(f"Reversing seed decision failed: {exc}")
            seed = {
                "thought": "LLM decision failed.",
                "targets": [],
            }

        raw_targets = seed.get("targets")
        targets = self.targets.prepare_targets(raw_targets, source="seed")
        if isinstance(raw_targets, list) and raw_targets and not targets:
            seed_error = self._append_error(
                seed_error,
                "Seed returned no valid reversing targets.",
            )

        source = "seed"

        return seed, targets, source, seed_error

    def _entrypoint_baseline_targets(self) -> list[dict[str, Any]]:
        try:
            items = entrypoints(str(self.context.sample))
        except Exception as exc:
            Logger.warning(f"Failed to collect entrypoint baseline: {exc}")
            return []

        for item in items:
            if not isinstance(item, dict):
                continue

            address = parse_address(item.get("vaddr"))
            if address is None:
                continue

            return [
                {
                    "tool": "disassembly",
                    "parameters": {
                        "address": hex(address),
                    },
                    "priority": ENTRY_POINT_BASE_PRIORITY,
                }
            ]

        return []

    def _append_error(
        self,
        current_error: str | None,
        message: str,
    ) -> str:
        if current_error:
            return f"{current_error}; {message}"

        return message
