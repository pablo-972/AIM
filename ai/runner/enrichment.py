from utils.logger import Logger
from utils.preprocessing import prepare_static_enrichment_sources, prepare_static_agent_sources
from utils.io.files import load_json
from utils.io.path import resolve_path
from utils.io.text import read_text, write_text
from config import RESULT_FILENAME, THREAT_ACTOR_MESSAGES_FILENAME, ENRICHMENT_FILENAME
from ai.runner.base import BaseAIRunner
from ai.generators.enrichment import EnrichmentGenerator


MARKDOWN_FENCE = "```"
ENRICHMENT_TITLE = "# Reverse Engineering Enrichment"
EMPTY_ENRICHMENT_BODY = "No information yet"


class EnrichmentAIRunner(BaseAIRunner):
    def __init__(self, context, model_registry):
        super().__init__(context)

        self.enrichment_path = resolve_path(self.context.output, ENRICHMENT_FILENAME)

        self.model_registry = model_registry
        llm = self.model_registry.create_task_client("enrichment", profile_override=self.context.profile)
        self.enrichment_generator = EnrichmentGenerator(llm)


    def _extract_body(self, content: str) -> str:
        lines = content.splitlines()
        if lines and lines[0].strip().lower() == ENRICHMENT_TITLE.lower():
            return "\n".join(lines[1:]).strip() or EMPTY_ENRICHMENT_BODY

        return content.strip()


    def _sanitize_enrichment(self, content: str | None) -> str:
        content = (content or "").strip()
        if not content or content == MARKDOWN_FENCE:
            return ""

        if content.startswith(MARKDOWN_FENCE) and content.endswith(MARKDOWN_FENCE):
            lines = content.splitlines()
            if len(lines) >= 2:
                content = "\n".join(lines[1:-1]).strip()

        return "" if content == MARKDOWN_FENCE else content


    def _build_document(self, body: str) -> str:
        body = self._sanitize_enrichment(body) or EMPTY_ENRICHMENT_BODY
        body = self._extract_body(body)
        return f"{ENRICHMENT_TITLE}\n\n{body.strip()}\n"


    def _load_current_enrichment(self) -> str:
        current = read_text(self.enrichment_path)
        current = self._sanitize_enrichment(current)
        if current:
            return self._extract_body(current)

        write_text(self.enrichment_path, self._build_document(EMPTY_ENRICHMENT_BODY))
        return EMPTY_ENRICHMENT_BODY
    

    def _save_enrichment(self, content: str):
        write_text(self.enrichment_path, self._build_document(content))


    def _get_sources(self) -> list[tuple[str, dict]]:
        result = load_json(self.context.output, RESULT_FILENAME) or {}
        static_agent_data = load_json(self.context.output, THREAT_ACTOR_MESSAGES_FILENAME) or {}

        sources = []
        sources.extend(prepare_static_enrichment_sources(result))
        sources.extend(prepare_static_agent_sources(static_agent_data))

        return sources


    def run(self):
        Logger.info("Running AI enrichment")

        current_enrichment = self._load_current_enrichment()

        for source_name, source_data in self._get_sources():
            Logger.info(f"Enriching from {source_name}")

            try:
                updated_enrichment = self.enrichment_generator.enrich(
                    current_enrichment=current_enrichment,
                    source_name=source_name,
                    source_data=source_data,
                )
            except Exception as exc:
                Logger.error(f"Enrichment failed for {source_name}: {exc}")
                continue

            updated_enrichment = self._sanitize_enrichment(updated_enrichment)
            if not updated_enrichment:
                Logger.warning(f"Empty enrichment response from {source_name}. Keeping previous content.")
                continue

            current_enrichment = self._extract_body(updated_enrichment)
            self._save_enrichment(current_enrichment)

        Logger.success("Finish enrichment")
