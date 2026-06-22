from collections.abc import Callable
from typing import Any


from tools.reversing.analyzers.disassembly import disassembly
from tools.reversing.analyzers.xrefs import xrefs, string_xrefs
from tools.reversing.analyzers.metadata import (
    binary_info,
    callees,
    callers,
    functions,
    imports,
    strings,
)


ManualTool = Callable[..., Any]


def run_string_xrefs(sample: str, string_value: str) -> dict[str, Any]:
    return string_xrefs(sample, string_value)


REVERSING_MANUAL_TOOLS: dict[str, ManualTool] = {
    "info": binary_info,
    "imports": imports,
    "functions": functions,
    "strings": strings,
    "disasm": disassembly,
    "xrefs": xrefs,
    "string-xrefs": run_string_xrefs,
    "callers": callers,
    "callees": callees,
}
