from typing import Any


FINAL_ASSESSMENT_HEADING = "## Assessment"
EVIDENCE_SUMMARY_HEADING = "### Evidence Summary"
MAX_EVIDENCE_ITEMS = 5


def normalize_final_assessment(
    report_markdown: str,
    assessment: dict[str, Any],
) -> str:
    evidence_items = extract_evidence_summary(report_markdown)
    cleaned_report = remove_final_assessment_section(report_markdown)
    assessment_section = build_final_assessment_section(
        assessment,
        evidence_items=evidence_items,
    )

    return insert_final_assessment_section(cleaned_report, assessment_section)


def build_final_assessment_section(
    assessment: dict[str, Any],
    evidence_items: list[str] | None = None,
) -> str:
    malware = "Yes" if assessment["is_malware"] else "No"
    malware_confidence = format_confidence(assessment["malware_confidence"])
    family = assessment["family"] or "Unknown"
    family_confidence = format_confidence(assessment["family_confidence"])
    categories = format_categories(assessment["categories"])
    evidence = evidence_items or [assessment["summary_reason"].strip()]
    evidence = evidence[:MAX_EVIDENCE_ITEMS]

    lines = [
        FINAL_ASSESSMENT_HEADING,
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Malware | {malware} |",
        f"| Malware confidence | {malware_confidence} |",
        f"| Family | {family} |",
        f"| Family confidence | {family_confidence} |",
        f"| Categories | {categories} |",
        "",
        EVIDENCE_SUMMARY_HEADING,
        "",
    ]

    for item in evidence:
        lines.append(f"- {item}")

    return "\n".join(lines).strip()


def format_confidence(value: int | float) -> str:
    percent = float(value) * 100
    if percent.is_integer():
        return f"{int(percent)}%"

    return f"{percent:.1f}%"


def format_categories(categories: list[str]) -> str:
    if not categories:
        return "None identified"

    return ", ".join(format_category(category) for category in categories)


def format_category(category: str) -> str:
    return category.replace("_", " ").replace("-", " ").title()


def extract_evidence_summary(report_markdown: str) -> list[str]:
    lines = report_markdown.splitlines()
    items: list[str] = []
    in_evidence_summary = False

    for line in lines:
        stripped = line.strip()
        if stripped == EVIDENCE_SUMMARY_HEADING:
            in_evidence_summary = True
            continue

        if in_evidence_summary and stripped.startswith("## "):
            break

        if not in_evidence_summary:
            continue

        if stripped.startswith("- "):
            item = stripped[2:].strip()
            if item:
                items.append(item)

        if len(items) >= MAX_EVIDENCE_ITEMS:
            break

    return items


def remove_final_assessment_section(report_markdown: str) -> str:
    lines = report_markdown.splitlines()
    kept_lines: list[str] = []
    skipping = False

    for line in lines:
        stripped = line.strip()
        if stripped == FINAL_ASSESSMENT_HEADING:
            skipping = True
            continue

        if skipping and stripped.startswith("## "):
            skipping = False

        if not skipping:
            kept_lines.append(line)

    return "\n".join(kept_lines).strip()


def insert_final_assessment_section(
    report_markdown: str,
    assessment_section: str,
) -> str:
    lines = report_markdown.splitlines()
    if not lines:
        return assessment_section

    first_line = lines[0].strip()
    if first_line.startswith("# "):
        remaining = "\n".join(lines[1:]).strip()
        parts = [
            lines[0].strip(),
            "",
            assessment_section,
        ]
        
        if remaining:
            parts.extend(["", remaining])

        return "\n".join(parts).strip()

    return f"{assessment_section}\n\n{report_markdown.strip()}".strip()
