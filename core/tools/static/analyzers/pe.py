import os
from typing import Any

import pefile

MACHINE_TYPES = {
    0x014C: "x86",
    0x8664: "x64",
    0x01C0: "ARM",
    0xAA64: "ARM64",
}


def analyze_pe(sample: str) -> dict[str, Any]:
    pe = pefile.PE(sample)

    return {
        "architecture": get_pe_architecture(pe),
        "sizes": get_pe_sizes(sample, pe),
        "subsystem": get_pe_subsystem(pe),
        "sections": get_pe_sections(pe),
        "imports": get_pe_imports(pe),
        "exports": get_pe_exports(pe),
        "delay_imports": get_pe_delay_imports(pe),
        "version_info": get_pe_version_info(pe),
        "resources": get_pe_resources(pe),
    }


def get_pe_architecture(pe: Any) -> str:
    machine = pe.FILE_HEADER.Machine

    return MACHINE_TYPES.get(machine, f"Unknown (0x{machine:04X})")


def get_pe_sections(pe: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "sections_count": pe.FILE_HEADER.NumberOfSections,
        "sections": []
    }

    for section in pe.sections:
        data["sections"].append(
            {
                "name": section.Name.decode().rstrip("\x00"),
                "relative_virtual_address": hex(section.VirtualAddress),
                "virtual_address": hex(pe.OPTIONAL_HEADER.ImageBase + section.VirtualAddress),
                "raw_size": section.SizeOfRawData,
                "virtual_size": section.Misc_VirtualSize,
                "entropy": section.get_entropy(),
            }
        )

    return data


def get_pe_imports(pe: Any) -> dict[str, list[str | None]]:
    if not hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        return {}
    
    imports: dict[str, list[str | None]] = {}

    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        dll_name = _decode_bytes(entry.dll)
        imports[dll_name] = [
            _decode_bytes(imp.name) if imp.name else None 
            for imp in entry.imports
        ]

    return imports


def get_pe_exports(pe: Any) -> list[str | None]:
    if not hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
        return []
    
    exports: list[str | None] = []

    for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        name = _decode_bytes(exp.name) if exp.name else None
        exports.append(name)

    return exports


def get_pe_delay_imports(pe: Any) -> dict[str, list[str | None]]:
    if not hasattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT"):
        return {}
    
    delay_imports: dict[str, list[str | None]] = {}

    for entry in pe.DIRECTORY_ENTRY_DELAY_IMPORT:
        dll_name = _decode_bytes(entry.dll)
        delay_imports[dll_name] = [
            _decode_bytes(imp.name) if imp.name else None
            for imp in entry.imports
        ]

    return delay_imports


def get_pe_version_info(pe: Any) -> dict[str, str]:
    if not hasattr(pe, "FileInfo"):
        return {}
    
    version_info: dict[str, str] = {}

    for fileinfo in pe.FileInfo:
        if fileinfo.Key == b"StringFileInfo":
            for st in fileinfo.StringTable:
                for k, v in st.entries.items():
                    version_info[_decode_bytes(k)] = _decode_bytes(v)

    return version_info


def get_pe_resources(pe: Any) -> list[str]:
    if not hasattr(pe, "DIRECTORY_ENTRY_RESOURCE"):
        return []
    
    resources: list[str] = []
    
    for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if entry.name:
            resources.append(str(entry.name)) 
        else: 
            resources.append(str(entry.struct.Id))

    return resources


def get_pe_sizes(sample: str, pe: Any) -> dict[str, int]:
    return {
        "raw_file_size": os.path.getsize(sample),
        "memory_file_size": pe.OPTIONAL_HEADER.SizeOfImage
    }


def get_pe_subsystem(pe: Any) -> str:
    subsystem = pe.OPTIONAL_HEADER.Subsystem
    value = pefile.SUBSYSTEM_TYPE.get(subsystem, "unknown")
    
    return value if isinstance(value, str) else str(value)


def is_pe(sample: str) -> bool:
    try:
        pefile.PE(sample)
    except pefile.PEFormatError:
        return False
    
    return True


def _decode_bytes(value: bytes) -> str:
    return value.decode(errors="ignore")