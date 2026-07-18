from typing import Any

from config import (
    DYNAMIC_INFERENCE_RESULT_FILENAME,
    ENRICHMENT_FILENAME,
    RESULT_FILENAME,
    STATIC_STRINGS_INFERENCE_RESULT_FILENAME,
)
from core.utils.logger import Logger
from core.utils.io.files import load_json
from core.utils.artifacts.documents import ENRICHMENT_TITLE, MarkdownDocument
from core.utils.preprocessing import (
    prepare_dynamic_artifact_sources,
    prepare_dynamic_inference_sources,
    prepare_static_enrichment_sources,
    prepare_static_inference_sources,
)
from core.orchestrator.context import AnalysisContext
from core.ai.model_registry import ModelRegistry
from core.ai.runner.base import BaseAIRunner
from core.ai.inferences.enrichment import EnrichmentGenerator


class EnrichmentAIRunner(BaseAIRunner):
    def __init__(self, context: AnalysisContext, model_registry: ModelRegistry) -> None:
        super().__init__(context)

        enrichment_path = self.context.output / ENRICHMENT_FILENAME
        self.document: MarkdownDocument = MarkdownDocument(
            enrichment_path, 
            ENRICHMENT_TITLE,
        )
        
        self.model_registry = model_registry
        

    def run(self) -> None:
        Logger.info("Running AI enrichment")

        current_body = self.document.load_body()

        for source_name, source_data in self._get_sources():
            Logger.info(f"Enriching from {source_name}")

            updated_body = self._generate_enrichment(
                current_body,
                source_name,
                source_data,
            )
            if updated_body is None:
                continue

            current_body = updated_body
            self.document.save_body(current_body)

        Logger.success("Enrichment finished")


    def _generate_enrichment(
        self,
        current_body: str,
        source_name: str,
        source_data: Any,
    ) -> str | None:
        generator = self._create_generator()

        try:
            updated_body = generator.enrich(
                current_enrichment=current_body,
                source_name=source_name,
                source_data=source_data,
            )
        except Exception as exc:
            Logger.error(f"Enrichment failed for {source_name}: {exc}")
            return None

        updated_body = self.document.sanitize(updated_body)
        if not updated_body:
            Logger.warning(
                f"Empty enrichment response from {source_name}. Keeping previous content."
            )
            return None

        return self.document.extract_body(updated_body)

    def _get_sources(self) -> list[tuple[str, Any]]:
        result = load_json(self.context.output, RESULT_FILENAME) or {}
        
        static_inference_data = (
            load_json(self.context.output, STATIC_STRINGS_INFERENCE_RESULT_FILENAME)
            or {}
        )
        dynamic_inference_data = (
            load_json(self.context.output, DYNAMIC_INFERENCE_RESULT_FILENAME)
            or {}
        )
        return [
            *prepare_static_enrichment_sources(result),
            *prepare_static_inference_sources(static_inference_data),
            *prepare_dynamic_artifact_sources(result),
            *prepare_dynamic_inference_sources(dynamic_inference_data),
        ]
    
    
    def _create_generator(self) -> EnrichmentGenerator:
        llm = self.model_registry.create_task_client(
            "enrichment", 
            profile_override=self.context.profile,
        )

        return EnrichmentGenerator(llm)

