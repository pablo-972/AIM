from typing import Any

from config import (
    ASSESSMENT_FILENAME,
    DYNAMIC_INFERENCE_RESULT_FILENAME,
    ENRICHMENT_FILENAME,
    REPORT_FILENAME,
    RESULT_FILENAME,
    REVERSING_AGENT_RESULT_FILENAME,
    STATIC_STRINGS_INFERENCE_RESULT_FILENAME,
)
from core.utils.artifacts.extractor import JsonExtractor, batched_findings
from core.utils.artifacts.documents import (
    EMPTY_DOCUMENT_BODY,
    ENRICHMENT_TITLE,
    MarkdownDocument,
    REPORT_TITLE,
)
from core.utils.io.files import load_json, save_json
from core.utils.io.text import read_text
from core.utils.logger import Logger
from core.utils.postprocessing.assessment import normalize_final_assessment
from core.utils.preprocessing import (
    group_sources_by_phase,
    prepare_dynamic_artifact_sources,
    prepare_dynamic_inference_sources,
    prepare_report_sources,
    prepare_static_inference_sources,
)
from core.ai.inferences.report import ReportGenerator
from core.ai.model_registry import ModelRegistry
from core.ai.runner.base import BaseAIRunner
from core.orchestrator.context import AnalysisContext


CLOUD_PROVIDER_TYPES = {"gemini", "openai"}


class ReportAIRunner(BaseAIRunner):
    def __init__(
        self, 
        context: AnalysisContext, 
        model_registry: ModelRegistry,
    ) -> None:
        super().__init__(context)

        report_path = self.context.output / REPORT_FILENAME
        self.document: MarkdownDocument = MarkdownDocument(
            report_path, 
            REPORT_TITLE,
        )

        enrichment_path = self.context.output / ENRICHMENT_FILENAME
        self.enrichment_document: MarkdownDocument = MarkdownDocument(
            enrichment_path,
            ENRICHMENT_TITLE,
        )

        self.model_registry = model_registry

    def run(self) -> None:
        Logger.info("Running AI report")

        current_body = self.document.load_body()
        sources = self._get_sources()
        if not sources:
            Logger.success("Report finished")
            return

        generator = self._create_generator()

        for source_name, source_data in sources:
            Logger.info(f"Reporting from {source_name}")

            updated_body = self._generate_report_update(
                generator,
                current_body,
                source_name,
                source_data,
            )
            if updated_body is None:
                continue

            current_body = updated_body
            self.document.save_body(current_body)

        if self._finalize_report(generator, current_body):
            Logger.success("Report finished")


    def _get_sources(self) -> list[tuple[str, Any]]:
        sources = [
            *self._get_static_sources(),
            *self._get_static_inference_sources(),
            *self._get_dynamic_artifact_sources(),
            *self._get_dynamic_inference_sources(),
            *self._get_enrichment_sources(),
            *self._get_reversing_agent_sources(),
        ]

        if self._uses_cloud_profile():
            return group_sources_by_phase(sources)

        return sources

    def _generate_report_update(
        self,
        generator: ReportGenerator,
        current_body: str,
        source_name: str,
        source_data: Any,
    ) -> str | None:
        try:
            updated_body = generator.update_report(
                current_report=current_body,
                source_name=source_name,
                source_data=source_data,
            )
        except Exception as exc:
            Logger.error(f"Report failed for {source_name}: {exc}")
            return None

        updated_body = self.document.sanitize(updated_body)
        if not updated_body:
            Logger.warning(
                f"Empty report response from {source_name}. Keeping previous content."
            )
            return None

        return self.document.extract_body(updated_body)

    def _finalize_report(
        self,
        generator: ReportGenerator,
        current_body: str,
    ) -> bool:
        try:
            generated_report = generator.finalize_report(current_body)
        except Exception as exc:
            Logger.error(f"Structured report generation failed: {exc}")
            return False

        report_markdown = normalize_final_assessment(
            generated_report.report_markdown,
            generated_report.assessment,
        )
        report_markdown = self.document.sanitize(report_markdown)
        if not report_markdown:
            Logger.error("Structured report generation returned empty Markdown.")
            return False

        final_body = self.document.extract_body(report_markdown)
        save_json(
            self.context.output,
            ASSESSMENT_FILENAME,
            generated_report.assessment,
        )
        self.document.save_body(final_body)
        
        return True


    def _get_static_sources(self) -> list[tuple[str, Any]]:
        extractor = self._get_analysis_extractor()
        if extractor is None:
            return []

        sources: list[tuple[str, Any]] = []
        for tool_name in extractor.get_phase_tools("static"):
            tool_data = extractor.get_phase_tool_data("static", tool_name)
            if tool_data is None:
                continue

            sources.extend(prepare_report_sources(tool_name, tool_data))

        return sources
        
    def _get_static_inference_sources(self) -> list[tuple[str, Any]]:
        data = load_json(self.context.output, STATIC_STRINGS_INFERENCE_RESULT_FILENAME)
        findings = prepare_static_inference_sources(data or {})

        return findings

    def _get_dynamic_inference_sources(self) -> list[tuple[str, Any]]:
        data = load_json(self.context.output, DYNAMIC_INFERENCE_RESULT_FILENAME)
        findings = prepare_dynamic_inference_sources(data or {})

        return findings

    def _get_dynamic_artifact_sources(self) -> list[tuple[str, Any]]:
        data = load_json(self.context.output, RESULT_FILENAME)
        sources = prepare_dynamic_artifact_sources(data or {})

        return sources

    def _get_enrichment_sources(self) -> list[tuple[str, Any]]:
        text = read_text(self.enrichment_document.path)

        content = self.enrichment_document.sanitize(text)
        if not content:
            return []

        body = self.enrichment_document.extract_body(content)
        if not body or body == EMPTY_DOCUMENT_BODY:
            return []

        return [("reverse_engineering_enrichment", body)]

    def _get_reversing_agent_sources(self) -> list[tuple[str, Any]]:
        data = load_json(self.context.output, REVERSING_AGENT_RESULT_FILENAME)
        findings = JsonExtractor(data).get_findings()
        batches = batched_findings(findings, batch_size=2)

        return [
            (
                f"reversing_agent.findings.{index}",
                {
                    "findings": batch,
                    "findings_count": len(batch),
                },
            )
            for index, batch in enumerate(batches, start=1)
        ]

    def _create_generator(self) -> ReportGenerator:
        llm = self.model_registry.create_task_client(
            "report", 
            profile_override=self.context.profile,
        )

        return ReportGenerator(llm)

    def _uses_cloud_profile(self) -> bool:
        provider_type = self.model_registry.get_task_provider_type(
            "report",
            profile_override=self.context.profile,
        )

        return provider_type in CLOUD_PROVIDER_TYPES

    def _get_analysis_extractor(self) -> JsonExtractor | None:
        result = load_json(self.context.output, RESULT_FILENAME)

        if not result:
            Logger.warning("No analysis data found. Skipping static report section.")
            return None

        return JsonExtractor(result)
