from typing import Any

from config import (
    ENRICHMENT_FILENAME,
    REPORT_FILENAME,
    RESULT_FILENAME,
    REVERSING_AGENT_RESULT_FILENAME,
    STATIC_STRINGS_INFERENCE_RESULT_FILENAME,
)
from utils.artifacts.extractor import JsonExtractor, batched_findings
from utils.artifacts.documents import (
    EMPTY_DOCUMENT_BODY,
    ENRICHMENT_TITLE,
    MarkdownDocument,
    REPORT_TITLE,
)
from utils.io.files import load_json
from utils.io.text import read_text
from utils.logger import Logger
from utils.preprocessing import prepare_report_chunks
from ai.inferences.report import ReportGenerator
from ai.model_registry import ModelRegistry
from ai.runner.base import BaseAIRunner
from orchestrator.context import AnalysisContext


class ReportAIRunner(BaseAIRunner):
    def __init__(
        self,
        context: AnalysisContext,
        model_registry: ModelRegistry,
    ) -> None:
        super().__init__(context)

        report_path = self.context.output / REPORT_FILENAME
        self.document: MarkdownDocument = MarkdownDocument(report_path, REPORT_TITLE)

        enrichment_path = self.context.output / ENRICHMENT_FILENAME
        self.enrichment_document: MarkdownDocument = MarkdownDocument(
            enrichment_path,
            ENRICHMENT_TITLE,
        )

        llm = model_registry.create_task_client("report", profile_override=self.context.profile)
        self.generator: ReportGenerator = ReportGenerator(llm)

    def run(self) -> None:
        Logger.info("Running AI report")

        current_body = self.document.load_body()
        for source_name, source_data in self._get_sources():
            Logger.info(f"Reporting from {source_name}")
            try:
                updated_body = self.generator.update_report(
                    current_report=current_body,
                    source_name=source_name,
                    source_data=source_data,
                )
            except Exception as exc:
                Logger.error(f"Report failed for {source_name}: {exc}")
                continue

            updated_body = self.document.sanitize(updated_body)
            if not updated_body:
                Logger.warning(f"Empty report response from {source_name}. Keeping previous content.")
                continue

            current_body = self.document.extract_body(updated_body)
            self.document.save_body(current_body)

        Logger.success("Report finished")

    def _get_static_extractor(self) -> JsonExtractor | None:
        result = load_json(self.context.output, RESULT_FILENAME)
        if not result:
            Logger.warning("No static analysis data found. Skipping static report section.")
            return None

        return JsonExtractor(result)

    def _build_source_name(
            self, 
            tool_name: str, 
            chunk_data: Any,
            chunk_index: int, 
            total_chunks: int
        ) -> str:
        section = chunk_data.get("section") if isinstance(chunk_data, dict) else None
        if section:
            return f"static.{tool_name}.{section}"

        if total_chunks > 1:
            return f"static.{tool_name}.{chunk_index}"

        return f"static.{tool_name}"

    def _get_static_sources(self) -> list[tuple[str, Any]]:
        extractor = self._get_static_extractor()
        if extractor is None:
            return []

        sources: list[tuple[str, Any]] = []
        for tool_name in extractor.get_phase_tools("static"):
            tool_data = extractor.get_phase_tool_data("static", tool_name)
            if tool_data is None:
                continue

            chunks = prepare_report_chunks(tool_name, tool_data)
            for chunk_index, chunk_data in enumerate(chunks, start=1):
                source_name = self._build_source_name(
                    tool_name,
                    chunk_data,
                    chunk_index,
                    len(chunks),
                )
                sources.append((source_name, chunk_data))

        return sources

    def _get_static_inference_sources(self) -> list[tuple[str, Any]]:
        data = load_json(self.context.output, STATIC_STRINGS_INFERENCE_RESULT_FILENAME)
        findings = JsonExtractor(data).get_static_inference_findings()

        return [
            (
                f"static_strings_inference.findings.{index}",
                {
                    "confidence": finding.get("confidence"),
                    "text": finding.get("text"),
                    "category": finding.get("category"),
                    "tone": finding.get("tone"),
                },
            )
            for index, finding in enumerate(findings, start=1)
        ]

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

    def _get_enrichment_sources(self) -> list[tuple[str, Any]]:
        content = self.enrichment_document.sanitize(
            read_text(self.enrichment_document.path)
        )
        if not content:
            return []

        body = self.enrichment_document.extract_body(content)
        if not body or body == EMPTY_DOCUMENT_BODY:
            return []

        return [("reverse_engineering_enrichment", body)]

    def _get_sources(self) -> list[tuple[str, Any]]:
        return [
            *self._get_static_sources(),
            *self._get_static_inference_sources(),
            *self._get_enrichment_sources(),
            *self._get_reversing_agent_sources(),
        ]
