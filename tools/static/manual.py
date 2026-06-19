from collections.abc import Callable
from typing import Any

from tools.static.analyzers.file import analyze_file
from tools.static.analyzers.hash import calculate_hashes
from tools.static.analyzers.metadata import analyze_metadata
from tools.static.analyzers.packer import detect_packer
from tools.static.analyzers.pe import analyze_pe
from tools.static.analyzers.strings import analyze_strings
from tools.static.analyzers.virustotal import get_vt_data


ManualTool = Callable[..., Any]


STATIC_MANUAL_TOOLS: dict[str, ManualTool] = {
    "file": analyze_file,
    "metadata": analyze_metadata,
    "hash": calculate_hashes,
    "packer": detect_packer,
    "strings": analyze_strings,
    "pe": analyze_pe,
    "vt": get_vt_data,
}
