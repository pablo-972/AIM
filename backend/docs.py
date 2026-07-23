from pathlib import Path
from typing import Any

from config import DOCS_PATH
from core.exceptions import DocumentationNotFoundError


DOCS: dict[str, tuple[str, Path]] = {
    "getting-started": ("Getting Started", DOCS_PATH / "getting-started" / "README.md"),
    "getting-started/configuration": ("Configuration", DOCS_PATH / "getting-started" / "configuration.md"),
    "getting-started/deployment": ("Deployment", DOCS_PATH / "getting-started" / "deployment.md"),
    "getting-started/malware-lab": ("Malware Lab", DOCS_PATH / "getting-started" / "malware-lab.md"),
    "getting-started/software-agents": ("Software Agents", DOCS_PATH / "getting-started" / "software-agents.md"),
    "phases": ("Phases", DOCS_PATH / "phases" / "README.md"),
    "phases/static": ("Static Analysis", DOCS_PATH / "phases" / "static.md"),
    "phases/dynamic": ("Dynamic Analysis", DOCS_PATH / "phases" / "dynamic.md"),
    "phases/enrichment": ("Enrichment", DOCS_PATH / "phases" / "enrichment.md"),
    "phases/reversing": ("Reverse Engineering", DOCS_PATH / "phases" / "reversing.md"),
    "phases/report": ("Report", DOCS_PATH / "phases" / "report.md"),
    "tools": ("Tools", DOCS_PATH / "tools" / "README.md"),
    "tools/static": ("Static Tools", DOCS_PATH / "tools" / "static.md"),
    "tools/dynamic": ("Dynamic Tools", DOCS_PATH / "tools" / "dynamic.md"),
    "tools/reversing": ("Reversing Tools", DOCS_PATH / "tools" / "reversing.md"),
    "ai": ("AI", DOCS_PATH / "ai" / "README.md"),
    "architecture": ("Architecture", DOCS_PATH / "architecture" / "README.md"),
    "troubleshooting": ("Troubleshooting", DOCS_PATH / "troubleshooting" / "README.md"),
}

def get_document(slug: str) -> dict[str, Any]:
    normalized_slug = normalize_doc_slug(slug)
    entry = DOCS.get(normalized_slug)
    if entry is None:
        raise DocumentationNotFoundError("Documentation page not found")

    title, path = entry
    if not path.exists() or not path.is_file():
        raise DocumentationNotFoundError("Documentation page not found")

    return {
        "slug": normalized_slug,
        "title": title,
        "content": path.read_text(encoding="utf-8"),
    }


def normalize_doc_slug(slug: str) -> str:
    normalized = slug.strip().strip("/")
    if not normalized:
        return "getting-started"

    if normalized.endswith(".md"):
        normalized = normalized[:-3]

    if normalized.endswith("/README"):
        normalized = normalized[:-7]

    return normalized
