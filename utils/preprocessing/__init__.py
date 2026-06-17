
from utils.preprocessing.chunks import prepare_generic_report_chunks
from utils.preprocessing.pe import prepare_pe_enrichment_sources, prepare_pe_report_chunks
from utils.preprocessing.virustotal import prepare_vt_enrichment_data, prepare_vt_report_chunks


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


def prepare_strings_report_data(tool_data: dict) -> dict:
    data = dict(tool_data)
    parsed_strings = data.pop("parsed_strings", [])
    data["parsed_strings_count"] = len(parsed_strings)

    return data


def prepare_tool_data(tool_name: str, tool_data):
    if tool_name == "strings":
        return prepare_strings_report_data(tool_data)

    return tool_data


def prepare_report_chunks(tool_name: str, tool_data) -> list[dict]:
    prepared_data = prepare_tool_data(tool_name, tool_data)

    if tool_name == "pe" and isinstance(prepared_data, dict):
        return prepare_pe_report_chunks(prepared_data)

    if tool_name in {"vt", "virustotal"} and isinstance(prepared_data, dict):
        return prepare_vt_report_chunks(prepared_data)

    return prepare_generic_report_chunks(tool_name, prepared_data)


def prepare_static_enrichment_sources(result: dict) -> list[tuple[str, dict]]:
    sources = []

    file_data = get_tool_data(result, "file")
    if file_data:
        sources.append(("static.file", {"file_type": file_data}))

    metadata = get_tool_data(result, "metadata")
    if metadata:
        sources.append(("static.metadata", metadata))

    packer = get_tool_data(result, "packer")
    if packer:
        sources.append(("static.packer", packer))

    strings = get_tool_data(result, "strings")
    if strings:
        strings_data = dict(strings)
        parsed_strings = strings_data.pop("parsed_strings", [])
        strings_data["parsed_strings_count"] = len(parsed_strings)
        sources.append(("static.strings.filtered", strings_data))

    pe = get_tool_data(result, "pe")
    if pe:
        sources.extend(
            (f"static.pe.{source_name}", source_data)
            for source_name, source_data in prepare_pe_enrichment_sources(pe)
        )

    vt = get_tool_data(result, "vt") or get_tool_data(result, "virustotal")
    if vt:
        sources.append(("static.virustotal", prepare_vt_enrichment_data(vt)))

    return sources


def prepare_static_agent_sources(static_agent_data: dict) -> list[tuple[str, dict]]:
    if not static_agent_data:
        return []

    message_blocks = [
        filtered_block
        for block in get_threat_actor_message_blocks(static_agent_data)
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


def _filter_actor_message_block(message_block: list[str]) -> list[str]:
    filtered = []

    for line in message_block:
        normalized = line.strip()
        if not normalized:
            continue

        lower = normalized.lower()
        if any(lower.startswith(prefix) for prefix in ACTOR_MESSAGE_NOISE_PREFIXES):
            continue

        if any(keyword in lower for keyword in ACTOR_MESSAGE_KEYWORDS):
            filtered.append(normalized)

    return filtered
