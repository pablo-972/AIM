from typing import Any

from core.utils.chunks import prepare_generic_report_chunks
from core.utils.preprocessing.static.pe import prepare_pe_report_chunks
from core.utils.preprocessing.static.virustotal import prepare_vt_report_chunks


def prepare_strings_report_data(tool_data: dict[str, Any]) -> dict[str, Any]:
    data = dict(tool_data)

    parsed_strings = data.pop("parsed_strings", [])
    count = len(parsed_strings) if isinstance(parsed_strings, list) else 0

    data["parsed_strings_count"] = count

    return data


def prepare_tool_data(tool_name: str, tool_data: Any) -> Any:
    if tool_name == "strings" and isinstance(tool_data, dict):
        return prepare_strings_report_data(tool_data)

    return tool_data


def prepare_report_chunks(tool_name: str, tool_data: Any) -> list[Any]:
    prepared_data = prepare_tool_data(tool_name, tool_data)

    if tool_name == "pe" and isinstance(prepared_data, dict):
        return prepare_pe_report_chunks(prepared_data)

    if tool_name in {"vt", "virustotal"} and isinstance(prepared_data, dict):
        return prepare_vt_report_chunks(prepared_data)

    return prepare_generic_report_chunks(tool_name, prepared_data)
