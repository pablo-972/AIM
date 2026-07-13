from typing import Any


NO_TOOL_ACTIONS = {"none", "finish"}
CODE_FOLLOW_UP_TOOLS = {"function", "disassembly", "callers", "callees"}
XREF_TOOLS = {"string_xrefs", "import_xrefs"}


def is_empty_code_observation(observation: dict[str, Any]) -> bool:
    return (
        observation.get("returned_instructions") == 0
        or observation.get("instructions_count") == 0
    )
