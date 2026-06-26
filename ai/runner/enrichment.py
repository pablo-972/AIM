from typing import Any

from config import (
    ENRICHMENT_FILENAME,
    RESULT_FILENAME,
    STATIC_STRINGS_INFERENCE_RESULT_FILENAME,
)
from utils.io.files import load_json
from utils.logger import Logger
from utils.artifacts.documents import ENRICHMENT_TITLE, MarkdownDocument
from utils.preprocessing import (
    prepare_static_enrichment_sources,
    prepare_static_inference_sources,
)
from ai.inferences.enrichment import EnrichmentGenerator
from ai.model_registry import ModelRegistry
from ai.runner.base import BaseAIRunner
from orchestrator.context import AnalysisContext


class EnrichmentAIRunner(BaseAIRunner):
    def __init__(
        self,
        context: AnalysisContext,
        model_registry: ModelRegistry,
    ) -> None:
        super().__init__(context)

        enrichment_path = self.context.output / ENRICHMENT_FILENAME
        self.document: MarkdownDocument = MarkdownDocument(
            enrichment_path,
            ENRICHMENT_TITLE,
        )

        llm = model_registry.create_task_client("enrichment", profile_override=self.context.profile)
        self.generator: EnrichmentGenerator = EnrichmentGenerator(llm)

    def run(self) -> None:
        Logger.info("Running AI enrichment")

        current_body = self.document.load_body()
        for source_name, source_data in self._get_sources():
            Logger.info(f"Enriching from {source_name}")
            try:
                updated_body = self.generator.enrich(
                    current_enrichment=current_body,
                    source_name=source_name,
                    source_data=source_data,
                )
            except Exception as exc:
                Logger.error(f"Enrichment failed for {source_name}: {exc}")
                continue

            updated_body = self.document.sanitize(updated_body)
            if not updated_body:
                Logger.warning(f"Empty enrichment response from {source_name}. Keeping previous content.")
                continue

            current_body = self.document.extract_body(updated_body)
            self.document.save_body(current_body)

        Logger.success("Enrichment finished")

    def _get_sources(self) -> list[tuple[str, Any]]:
        result = load_json(self.context.output, RESULT_FILENAME) or {}
        static_inference_data = (
            load_json(self.context.output, STATIC_STRINGS_INFERENCE_RESULT_FILENAME)
            or {}
        )
        return [
            *prepare_static_enrichment_sources(result),
            *prepare_static_inference_sources(static_inference_data),
        ]
    
    

