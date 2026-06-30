from pathlib import Path
from typing import Any

import pefile

from utils.io.commands import run_command

PACKER_NAMES = {
    ".upx0", 
    ".upx1", 
    ".aspack", 
    ".adata", 
    ".mpress1", 
    ".mpress2",
    "UPX0", 
    "UPX1", 
    "ASPack", 
    "FSG!", 
    "MEW",
}
ENTROPY_THRESHOLD = 7.3
SMALL_IMPORTS_THRESHOLD = 10
VIRTUAL_RAW_RATIO_THRESHOLD = 2.0


def detect_packer(path: str | Path) -> dict[str, Any]:
    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories()

    return {
        "packer_sections": _has_packer_section(pe),
        "high_entropy": _has_high_entropy(pe),
        "small_imports": _has_small_imports(pe),
        "section_anomalies": _is_virtual_larger_than_raw(pe),
        "upx": _is_upx_packed(path),
    }


def _get_section_name(section: Any) -> str:
    name = section.Name.decode(errors="ignore")

    return str(name).rstrip("\x00")


def _has_packer_section(pe: Any) -> dict[str, Any]:
    matches: list[str] = []

    for section in pe.sections:
        name = _get_section_name(section)
        packer_names = {packer_name.lower() for packer_name in PACKER_NAMES}

        if name.lower() in packer_names:
            matches.append(name)

    return {
        "detected": bool(matches),
        "matches": matches or None,
    }
    


def _has_high_entropy(pe: Any) -> dict[str, Any]:
    suspicious: list[dict[str, str | float]] = []

    for section in pe.sections:
        entropy = section.get_entropy()
        if entropy >= ENTROPY_THRESHOLD:
            suspicious.append(
                {
                    "section": _get_section_name(section),
                    "entropy": round(entropy, 2),
                }
            )
            
    return {
        "detected": bool(suspicious),
        "sections": suspicious or None,
    }


def _has_small_imports(pe: Any) -> dict[str, Any]:
    if not hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        return {
            "detected": True,
            "count": None,
            "reason": "no_imports",
        }
    
    total_imports = sum(len(entry.imports) for entry in pe.DIRECTORY_ENTRY_IMPORT)
    
    return {
        "detected": total_imports <= SMALL_IMPORTS_THRESHOLD,
        "count": total_imports,
    }


def _is_virtual_larger_than_raw(pe: Any) -> dict[str, Any]:
    anomalies: list[dict[str, str | int | float]] = []

    for section in pe.sections:
        raw = section.SizeOfRawData
        virtual = section.Misc_VirtualSize

        if raw == 0:
            continue

        ratio = virtual / raw
        if ratio > 2:
            anomalies.append(
                {
                    "section": _get_section_name(section),
                    "raw": raw,
                    "virtual": virtual,
                    "ratio": round(ratio, VIRTUAL_RAW_RATIO_THRESHOLD)
                }
            )

    return {
        "detected": bool(anomalies),
        "sections": anomalies or None,
    }


def _is_upx_packed(path: str | Path) -> dict[str, Any]:
    result = run_command(["upx", "-t", str(path)])
    output = f"{result.stdout}\n{result.stderr}"

    if result.timed_out:
        return {
            "detected": False,
            "packer": None,
            "reason": "timeout",
        }
    elif "NotPackedException" in output:
        return {
            "detected": False,
            "packer": None,
        }
    elif "packed" in output.lower():
        return {
            "detected": True,
            "packer": "UPX",
        }
    
    return {
        "detected": False,
        "packer": None,
    }
    
