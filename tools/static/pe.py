import os

import pefile


def is_pe(sample: str) -> bool:
    try:
        pe = pefile.PE(sample)
        return True
    except:
        return False


def get_pe_architecture(pe: pefile) -> str:
    return "x64" if pe.FILE_HEADER.Machine == 0x8664 else "x86"


def get_pe_sections(pe: pefile) -> dict:
    data = {
        "sections_count": pe.FILE_HEADER.NumberOfSections,
        "sections": []
    }
    for section in pe.sections:
        data["sections"].append({
            "name": section.Name.decode().rstrip("\x00"),
            "virtual_address": hex(section.VirtualAddress),
            "raw_size": section.SizeOfRawData,
            "virtual_size": section.Misc_VirtualSize,
            "entropy": section.get_entropy(),
        })
    return data


def get_pe_imports(pe: pefile) -> dict:
    imports = {}
    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            dll_name = entry.dll.decode(errors="ignore")
            imports[dll_name] = [imp.name.decode(errors="ignore") if imp.name else None for imp in entry.imports]
    return imports


def get_pe_exports(pe: pefile) -> list:
    exports = []
    if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
        for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            name = exp.name.decode(errors="ignore") if exp.name else None
            exports.append(name)
    return exports


def get_pe_delay_imports(pe: pefile) -> dict:
    delay_imports = {}
    if hasattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT"):
        for entry in pe.DIRECTORY_ENTRY_DELAY_IMPORT:
            dll_name = entry.dll.decode(errors="ignore")
            delay_imports[dll_name] = [imp.name.decode(errors="ignore") if imp.name else None
                                       for imp in entry.imports]
    return delay_imports


def get_pe_version_info(pe: pefile) -> dict:
    version_info = {}
    if hasattr(pe, "FileInfo"):
        for fileinfo in pe.FileInfo:
            if fileinfo.Key == b"StringFileInfo":
                for st in fileinfo.StringTable:
                    for k, v in st.entries.items():
                        version_info[k.decode(errors="ignore")] = v.decode(errors="ignore")
    return version_info


def get_pe_resources(pe: pefile) -> dict:
    resources = []
    if hasattr(pe, "DIRECTORY_ENTRY_RESOURCE"):
        for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
            resources.append(str(entry.name) if entry.name else str(entry.struct.Id))
    return resources


def get_pe_sizes(sample: str, pe: pefile) -> dict:
    data = {
        "raw_file_size": os.path.getsize(sample),
        "memory_file_size": pe.OPTIONAL_HEADER.SizeOfImage
    }
    return data
    

def get_pe_subsystem(pe: pefile) -> str:
    subsystem = pe.OPTIONAL_HEADER.Subsystem
    return pefile.SUBSYSTEM_TYPE.get(subsystem, "unknown")


def analyze_pe(sample: str) -> dict:
    pe = pefile.PE(sample)
    data = {}

    data["architecture"] = get_pe_architecture(pe)
    data["sizes"] = get_pe_sizes(sample, pe)
    data["subsystem"] = get_pe_subsystem(pe)
    data["sections"] = get_pe_sections(pe)
    data["imports"] = get_pe_imports(pe)
    data["exports"] = get_pe_exports(pe)
    data["delay_imports"] = get_pe_delay_imports(pe)
    data["version_info"] = get_pe_version_info(pe)
    data["resources"] = get_pe_resources(pe)

    return data



