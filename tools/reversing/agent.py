from collections.abc import Callable
from typing import Any

from tools.reversing.analyzers.analysis import (
    callees,
    callers,
    function_details,
    import_xrefs,
    string_xrefs,
    text_disassembly,
)


def get_string_xrefs(sample: str, value: str) -> dict[str, Any]:
    return string_xrefs(sample, value, include_all_strings=True)


ReversingAgentTool = Callable[..., Any]


REVERSING_AGENT_TOOLS: dict[str, ReversingAgentTool] = {
    "function": function_details,
    "disassembly": text_disassembly,
    "callers": callers,
    "callees": callees,
    "string_xrefs": get_string_xrefs,
    "import_xrefs": import_xrefs,
}
