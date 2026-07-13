from collections.abc import Callable
from typing import Any


from core.tools.reversing.analyzers.disassembly import disassembly
from core.tools.reversing.analyzers.xrefs import import_xrefs, string_xrefs, xrefs
from core.tools.reversing.analyzers.metadata import (
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
    "import-xrefs": import_xrefs,
    "callers": callers,
    "callees": callees,
}
