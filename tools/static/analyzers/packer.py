from pathlib import Path
from typing import Any

import pefile

from utils.io.commands import run_command


PACKER_NAMES = {
    ".upx0", ".upx1", ".aspack", 
    ".adata", ".mpress1", ".mpress2",
    "UPX0", "UPX1", "ASPack", 
    "FSG!", "MEW"
}
THRESHOLD_ENTROPY = 7.3


def get_section_name(section: Any) -> str:
    name = section.Name.decode(errors="ignore")
    return str(name).rstrip("\x00")


def has_packer_section(pe: Any) -> tuple[bool, list[str] | None]:
    matches: list[str] = []

    for section in pe.sections:
        name = get_section_name(section)
        if name in PACKER_NAMES:
            matches.append(name)

    return (len(matches) > 0, matches if matches else None)


def has_high_entropy(pe: Any) -> tuple[bool, list[dict[str, str | float]] | None]:
    suspicious: list[dict[str, str | float]] = []

    for section in pe.sections:
        entropy = section.get_entropy()
        if entropy >= THRESHOLD_ENTROPY:
            suspicious.append({
                "section": get_section_name(section),
                "entropy": round(entropy, 2)
            })
            
    return (len(suspicious) > 0, suspicious if suspicious else None)


def has_small_imports(pe: Any) -> tuple[bool, int | str]:
    if not hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        return (True, "no_imports")
    total_imports = sum(len(entry.imports) for entry in pe.DIRECTORY_ENTRY_IMPORT)
    if total_imports <= 10:
        return (True, total_imports)
    return (False, total_imports)


def is_virtual_larger_than_raw(
    pe: Any,
) -> tuple[bool, list[dict[str, str | int | float]] | None]:
    anomalies: list[dict[str, str | int | float]] = []
    for section in pe.sections:
        raw = section.SizeOfRawData
        virtual = section.Misc_VirtualSize
        if raw == 0:
            continue
        ratio = virtual / raw
        if ratio > 2:
            anomalies.append({
                "section": get_section_name(section),
                "raw": raw,
                "virtual": virtual,
                "ratio": round(ratio, 2)
            })
    return (len(anomalies) > 0, anomalies if anomalies else None)


def is_upx_packed(path: str | Path) -> tuple[bool, str | None]:
    result = run_command(["upx", "-t", str(path)])
    output = f"{result.stdout}\n{result.stderr}"
    if result.timed_out:
        return (False, "upx_timeout")
    if "NotPackedException" in output:
        return (False, None)
    if "packed" in output.lower():
        return (True, "UPX")
    return (False, None)


def detect_packer(path: str | Path) -> dict[str, Any]:
    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories()

    results: dict[str, Any] = {}

    results["packer_sections"] = has_packer_section(pe)
    results["high_entropy"] = has_high_entropy(pe)
    results["small_imports"] = has_small_imports(pe)
    results["section_anomalies"] = is_virtual_larger_than_raw(pe)
    results["upx"] = is_upx_packed(path)

    return results
