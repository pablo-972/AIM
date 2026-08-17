from typing import Any

from config import (
    DYNAMIC_INFERENCE_RESULT_FILENAME,
    ENRICHMENT_FILENAME,
    RESULT_FILENAME,
    STATIC_INFERENCE_RESULT_FILENAME,
)
from core.utils.artifacts.extractor import JsonExtractor
from core.utils.logger import Logger
from core.utils.io.files import load_json
from core.utils.artifacts.documents import ENRICHMENT_TITLE, MarkdownDocument
from core.utils.preprocessing import (
    group_sources_by_phase,
    prepare_dynamic_artifact_sources,
    prepare_dynamic_inference_sources,
    prepare_report_sources,
    prepare_static_enrichment_sources,
    prepare_static_inference_sources,
)
from core.orchestrator.context import AnalysisContext
from core.ai.model_registry import ModelRegistry
from core.ai.runner.base import BaseAIRunner
from core.ai.inferences.enrichment import EnrichmentGenerator


CLOUD_PROVIDER_TYPES = {"gemini", "openai"}


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
        
        self.model_registry = model_registry
        

    def run(self) -> None:
        Logger.info("Running AI enrichment")

        current_body = self.document.load_body()
        sources = self._get_sources()
        if not sources:
            Logger.success("Enrichment finished")
            return

        generator = self._create_generator()

        for source_name, source_data in sources:
            Logger.info(f"Enriching from {source_name}")

            updated_body = self._generate_enrichment(
                generator,
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
        generator: EnrichmentGenerator,
        current_body: str,
        source_name: str,
        source_data: Any,
    ) -> str | None:
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
            load_json(self.context.output, STATIC_INFERENCE_RESULT_FILENAME)
            or {}
        )
        dynamic_inference_data = (
            load_json(self.context.output, DYNAMIC_INFERENCE_RESULT_FILENAME)
            or {}
        )

        if not self._uses_cloud_profile():
            return self._get_local_phase_sources(
                result,
                static_inference_data,
                dynamic_inference_data,
            )

        sources = [
            *prepare_static_enrichment_sources(result),
            *prepare_static_inference_sources(static_inference_data),
            *prepare_dynamic_artifact_sources(result),
            *prepare_dynamic_inference_sources(dynamic_inference_data),
        ]

        return group_sources_by_phase(sources)

    def _get_local_phase_sources(
        self,
        result: dict[str, Any],
        static_inference_data: dict[str, Any],
        dynamic_inference_data: dict[str, Any],
    ) -> list[tuple[str, dict[str, Any]]]:
        phases = [
            ("static.tools", self._get_static_tool_sources(result)),
            (
                "static.inference",
                prepare_static_inference_sources(static_inference_data),
            ),
            ("dynamic.tools", prepare_dynamic_artifact_sources(result)),
            (
                "dynamic.inference",
                prepare_dynamic_inference_sources(dynamic_inference_data),
            ),
        ]

        return [
            self._phase_source(phase_name, sources)
            for phase_name, sources in phases
            if sources
        ]

    def _get_static_tool_sources(
        self,
        result: dict[str, Any],
    ) -> list[tuple[str, Any]]:
        extractor = JsonExtractor(result)
        sources: list[tuple[str, Any]] = []

        for tool_name in extractor.get_phase_tools("static"):
            tool_data = extractor.get_phase_tool_data("static", tool_name)
            if tool_data is None:
                continue

            sources.extend(prepare_report_sources(tool_name, tool_data))

        return sources

    def _phase_source(
        self,
        phase_name: str,
        sources: list[tuple[str, Any]],
    ) -> tuple[str, dict[str, Any]]:
        return (
            phase_name,
            {
                "phase": phase_name,
                "source_count": len(sources),
                "sources": [
                    {
                        "source": source_name,
                        "data": source_data,
                    }
                    for source_name, source_data in sources
                ],
            },
        )
    
    
    def _create_generator(self) -> EnrichmentGenerator:
        llm = self.model_registry.create_task_client(
            "enrichment", 
            profile_override=self.context.profile,
        )

        return EnrichmentGenerator(llm)

    def _uses_cloud_profile(self) -> bool:
        provider_type = self.model_registry.get_task_provider_type(
            "enrichment",
            profile_override=self.context.profile,
        )

        return provider_type in CLOUD_PROVIDER_TYPES
