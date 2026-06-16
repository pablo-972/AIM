from utils.preprocessing.chunks import chunk_large_value, chunk_sequence, make_report_chunk


VT_SUMMARY_KEYS = [
    "md5",
    "sha1",
    "sha256",
    "authentihash",
    "ssdeep",
    "tlsh",
    "vhash",
    "meaningful_name",
    "names",
    "size",
    "type_description",
    "type_extension",
    "type_tag",
    "type_tags",
    "magic",
    "magika",
    "trid",
    "tags",
    "first_seen_itw_date",
    "first_submission_date",
    "last_submission_date",
    "last_analysis_date",
    "last_modification_date",
    "times_submitted",
    "reputation",
    "total_votes",
    "unique_sources",
]

VT_CLASSIFICATION_KEYS = [
    "popular_threat_classification",
    "last_analysis_stats",
    "sigma_analysis_stats",
    "sigma_analysis_summary",
]

VT_DIRECT_SECTION_KEYS = [
    "sandbox_verdicts",
    "crowdsourced_yara_results",
    "sigma_analysis_results",
]

VT_ENRICHMENT_KEYS = [
    "popular_threat_classification",
    "sandbox_verdicts",
    "tags",
    "meaningful_name",
    "last_analysis_stats",
]

MAX_ENRICHMENT_TAGS = 12

VT_ENGINE_CATEGORY_ORDER = [
    "malicious",
    "suspicious",
]


def extract_vt_attributes(vt_data: dict) -> dict:
    return (
        vt_data.get("data", {}).get("attributes")
        if isinstance(vt_data.get("data"), dict)
        else None
    ) or vt_data


def _pick_existing_keys(data: dict, keys: list[str]) -> dict:
    return {
        key: data.get(key)
        for key in keys
        if key in data
    }


def _prepare_engine_results(last_analysis_results: dict) -> dict[str, list[dict]]:
    grouped = {}

    for engine_name, result in last_analysis_results.items():
        category = result.get("category", "unknown")
        grouped.setdefault(category, []).append(
            {
                "engine": engine_name,
                "category": category,
                "result": result.get("result"),
                "method": result.get("method"),
                "engine_update": result.get("engine_update"),
            }
        )

    return grouped


def _ordered_engine_categories(grouped_results: dict[str, list[dict]]) -> list[str]:
    return [
        category
        for category in VT_ENGINE_CATEGORY_ORDER
        if category in grouped_results
    ]


def prepare_vt_report_chunks(vt_data: dict) -> list[dict]:
    attributes = extract_vt_attributes(vt_data)
    chunks = []

    summary = _pick_existing_keys(attributes, VT_SUMMARY_KEYS)
    if summary:
        chunks.append(make_report_chunk("summary", summary))

    classification = _pick_existing_keys(attributes, VT_CLASSIFICATION_KEYS)
    if classification:
        chunks.append(make_report_chunk("classification", classification))

    for key in VT_DIRECT_SECTION_KEYS:
        value = attributes.get(key)
        if value:
            chunks.extend(chunk_large_value(key, value))

    engine_results = attributes.get("last_analysis_results") or {}
    if engine_results:
        grouped_results = _prepare_engine_results(engine_results)
        for category in _ordered_engine_categories(grouped_results):
            chunks.extend(chunk_sequence(f"last_analysis_results.{category}", grouped_results[category]))

    return chunks or [make_report_chunk("raw", vt_data)]


def prepare_vt_enrichment_data(vt_data: dict) -> dict:
    attributes = extract_vt_attributes(vt_data)
    data = _pick_existing_keys(attributes, VT_ENRICHMENT_KEYS)

    if "tags" in data:
        data["tags"] = data["tags"][:MAX_ENRICHMENT_TAGS]

    return data
