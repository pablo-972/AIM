from collections.abc import Callable
from typing import Any

from tools.reversing.analyzers.metadata import callees, callers
from tools.reversing.analyzers.disassembly import function_details, text_disassembly
from tools.reversing.analyzers.xrefs import string_xrefs, import_xrefs

ReversingAgentTool = Callable[..., Any]


def get_string_xrefs(sample: str, value: str) -> dict[str, Any]:
    return string_xrefs(sample, value, include_all_strings=True)


REVERSING_AGENT_TOOLS: dict[str, ReversingAgentTool] = {
    "function": function_details,
    "disassembly": text_disassembly,
    "callers": callers,
    "callees": callees,
    "string_xrefs": get_string_xrefs,
    "import_xrefs": import_xrefs,
}








