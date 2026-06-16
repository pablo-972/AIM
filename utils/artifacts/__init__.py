
SCHEMA_VERSION = "1.0"


def build_analysis_result(sample_path: str, sample_size: int) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "sample": {
            "path": sample_path,
            "size": sample_size,
        },
        "phases": {},
    }


def build_phase(tools_results: dict) -> dict:
    return {
        "status": "completed",
        "tools": tools_results,
        "findings": [],
    }


def append_phase(result: dict | None, phase_name: str, phase_data: dict) -> dict:
    result = result or {}
    phases = result.setdefault("phases", {})
    phases[phase_name] = phase_data
    return result


def get_static_tools(result: dict | None) -> dict:
    return (
        (result or {})
        .get("phases", {})
        .get("static", {})
        .get("tools", {})
    )


def get_tool_result(result: dict | None, tool_name: str) -> dict:
    return get_static_tools(result).get(tool_name, {})


def get_tool_data(result: dict | None, tool_name: str):
    tool = get_tool_result(result, tool_name)
    if tool.get("status") != "ok":
        return None

    return tool.get("data")


def get_static_strings(result: dict | None) -> list[str]:
    strings_data = get_tool_data(result, "strings") or {}
    return strings_data.get("parsed_strings", [])


def get_threat_actor_message_blocks(static_agent_data: dict | None) -> list:
    return [
        item.get("message_block")
        for item in (static_agent_data or {}).get("items", [])
        if item.get("message_block")
    ]
