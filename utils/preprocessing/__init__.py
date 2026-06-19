
from typing import Any

from utils.preprocessing.chunks import prepare_generic_report_chunks
from utils.preprocessing.pe import prepare_pe_enrichment_sources, prepare_pe_report_chunks
from utils.preprocessing.virustotal import prepare_vt_enrichment_data, prepare_vt_report_chunks
from utils.artifacts.extractor import JsonExtractor


ACTOR_MESSAGE_KEYWORDS = [
    "ransom",
    "decrypt",
    "bitcoin",
    "btc",
    "wallet",
    "payment",
    "buy bitcoin",
    "contact us",
    "session from",
    ".onion",
    "stole",
    "lost your data",
    "we stole all your data",
    "your organization",
    "infiltrated",
    "do not attempt",
    "law enforcement",
    "funk",
    "congratulations",
    "what happened",
    "anti-virus",
    "restore",
    "sincerely",
    ".funksec",
]

ACTOR_MESSAGE_NOISE_PREFIXES = [
    "failed ",
    "invalid ",
    "internal error",
    "assertion failed",
    "called `result::unwrap",
    "unsupported",
    "chunk ",
    "unexpected eof",
    "error when",
]


def prepare_strings_report_data(
    tool_data: dict[str, Any],
) -> dict[str, Any]:
    data = dict(tool_data)
    parsed_strings = data.pop("parsed_strings", [])
    data["parsed_strings_count"] = (
        len(parsed_strings) if isinstance(parsed_strings, list) else 0
    )

    return data


def prepare_tool_data(tool_name: str, tool_data: Any) -> Any:
    if tool_name == "strings" and isinstance(tool_data, dict):
        return prepare_strings_report_data(tool_data)

    return tool_data


def prepare_report_chunks(
    tool_name: str,
    tool_data: Any,
) -> list[Any]:
    prepared_data = prepare_tool_data(tool_name, tool_data)

    if tool_name == "pe" and isinstance(prepared_data, dict):
        return prepare_pe_report_chunks(prepared_data)

    if tool_name in {"vt", "virustotal"} and isinstance(prepared_data, dict):
        return prepare_vt_report_chunks(prepared_data)

    return prepare_generic_report_chunks(tool_name, prepared_data)


def prepare_static_enrichment_sources(
    result: dict[str, Any],
) -> list[tuple[str, Any]]:
    sources: list[tuple[str, Any]] = []
    extractor = JsonExtractor(result)

    file_data = extractor.get_tool_data("file")
    if file_data:
        sources.append(("static.file", {"file_type": file_data}))

    metadata = extractor.get_tool_data("metadata")
    if metadata:
        sources.append(("static.metadata", metadata))

    packer = extractor.get_tool_data("packer")
    if isinstance(packer, dict) and packer:
        sources.append(("static.packer", packer))

    strings = extractor.get_tool_data("strings")
    if isinstance(strings, dict) and strings:
        strings_data = dict(strings)
        parsed_strings = strings_data.pop("parsed_strings", [])
        strings_data["parsed_strings_count"] = len(parsed_strings)
        sources.append(("static.strings.filtered", strings_data))

    pe = extractor.get_tool_data("pe")
    if isinstance(pe, dict) and pe:
        sources.extend(
            (f"static.pe.{source_name}", source_data)
            for source_name, source_data in prepare_pe_enrichment_sources(pe)
        )

    vt = extractor.get_tool_data("vt") or extractor.get_tool_data("virustotal")
    if isinstance(vt, dict) and vt:
        sources.append(("static.virustotal", prepare_vt_enrichment_data(vt)))

    return sources


def prepare_static_agent_sources(
    static_agent_data: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    if not static_agent_data:
        return []

    extractor = JsonExtractor(static_agent_data)
    message_blocks = [
        filtered_block
        for block in extractor.get_threat_actor_message_blocks()
        if (filtered_block := _filter_actor_message_block(block))
    ]
    if not message_blocks:
        return []

    return [
        (
            f"static_agent.threat_actor_messages.{index}",
            {"message_block": message_block},
        )
        for index, message_block in enumerate(message_blocks, start=1)
    ]


def _filter_actor_message_block(message_block: str | list[str]) -> list[str]:
    if isinstance(message_block, str):
        lines = message_block.splitlines()
    elif isinstance(message_block, list):
        lines = message_block
    else:
        return []

    filtered: list[str] = []

    for line in lines:
        if not isinstance(line, str):
            continue

        normalized = line.strip()
        if not normalized:
            continue

        lower = normalized.lower()
        if any(lower.startswith(prefix) for prefix in ACTOR_MESSAGE_NOISE_PREFIXES):
            continue

        if any(keyword in lower for keyword in ACTOR_MESSAGE_KEYWORDS):
            filtered.append(normalized)

    return filtered
