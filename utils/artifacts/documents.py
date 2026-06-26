from pathlib import Path

from utils.io.text import read_text, write_text


REPORT_TITLE = "# Malware Analysis Report"
ENRICHMENT_TITLE = "# Reverse Engineering Enrichment"
EMPTY_DOCUMENT_BODY = "No information yet"
MARKDOWN_FENCE = "```"


class MarkdownDocument:
    def __init__(self, path: Path, title: str) -> None:
        self.path: Path = path
        self.title: str = title

    def load_body(self) -> str:
        current = self.sanitize(read_text(self.path))
        if current:
            return self.extract_body(current)

        self.save_body(EMPTY_DOCUMENT_BODY)
        return EMPTY_DOCUMENT_BODY

    def save_body(self, body: str) -> None:
        write_text(self.path, self._build_document(body))

    def sanitize(self, content: str | None) -> str:
        content = (content or "").strip()
        if not content or content == MARKDOWN_FENCE:
            return ""

        if content.startswith(MARKDOWN_FENCE) and content.endswith(MARKDOWN_FENCE):
            lines = content.splitlines()
            if len(lines) >= 2:
                content = "\n".join(lines[1:-1]).strip()

        return "" if content == MARKDOWN_FENCE else content
    
    def extract_body(self, content: str) -> str:
        lines = content.splitlines()
        if lines and lines[0].strip().lower() == self.title.lower():
            return "\n".join(lines[1:]).strip() or EMPTY_DOCUMENT_BODY

        return content.strip()

    def _build_document(self, body: str) -> str:
        body = self.sanitize(body) or EMPTY_DOCUMENT_BODY
        body = self.extract_body(body)

        return f"{self.title}\n\n{body.strip()}\n"






