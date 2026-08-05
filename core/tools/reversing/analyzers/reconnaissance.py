from typing import Any

from core.tools.reversing.analyzers.metadata import functions, imports, strings


SUSPICIOUS_IMPORT_KEYWORDS = {
    "virtualalloc",
    "virtualprotect",
    "writeprocessmemory",
    "createremotethread",
    "loadlibrary",
    "getprocaddress",
    "createprocess",
    "shellexecute",
    "internet",
    "http",
    "crypt",
    "bcrypt",
    "regsetvalue",
    "createservice",
    "isdebuggerpresent",
}

INTERESTING_STRING_KEYWORDS = {
    "http",
    "cmd.exe",
    "powershell",
    "rundll32",
    "regsvr32",
    "schtasks",
    "service",
    "mutex",
    "bitcoin",
    "wallet",
    "decrypt",
    "encrypt",
    "ransom",
    "locker",
    "detected",
    "user-agent",
    "software\\",
}


def collect_reconnaissance(sample: str) -> dict[str, Any]:
    import_items = imports(sample)
    function_items = functions(sample)
    string_items = strings(sample)

    suspicious_imports = []
    for item in import_items:
        import_name = str(item.get("name", "")).lower()

        is_suspicious = any(
            keyword in import_name
            for keyword in SUSPICIOUS_IMPORT_KEYWORDS
        )

        if is_suspicious:
            suspicious_imports.append(item)

    suspicious_imports = suspicious_imports[:40]

    large_functions = sorted(
        function_items,
        key=lambda item: (
            item.get("size") or 0,
            item.get("instructions") or 0,
        ),
        reverse=True,
    )[:30]

    interesting_strings = []
    for item in string_items:
        string_value = item.get("string")

        if not isinstance(string_value, str):
            continue

        if not _is_clean_interesting_string(string_value):
            continue

        interesting_strings.append(
            {
                "value": string_value,
                "address": item.get("vaddr") or item.get("paddr"),
                "section": item.get("section"),
            }
        )

    interesting_strings = interesting_strings[:40]

    return {
        "suspicious_imports": suspicious_imports,
        "large_functions": large_functions,
        "interesting_strings": interesting_strings,
        "counts": {
            "imports": len(import_items),
            "functions": len(function_items),
            "strings": len(string_items),
        },
    }


def _is_clean_interesting_string(value: str) -> bool:
    if len(value) < 5:
        return False

    if len(value) > 256:
        return False

    for character in value:
        if ord(character) < 32 and not character.isspace():
            return False

    normalized_value = value.lower()

    for keyword in INTERESTING_STRING_KEYWORDS:
        if keyword in normalized_value:
            return True

    return False



