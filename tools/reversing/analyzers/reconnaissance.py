from typing import Any

from tools.reversing.analyzers.metadata import functions, imports, strings


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


def _is_clean_interesting_string(value: str) -> bool:
    if not 5 <= len(value) <= 256:
        return False

    if any(ord(character) < 32 and not character.isspace() for character in value):
        return False

    return any(
        keyword in value.lower()
        for keyword in INTERESTING_STRING_KEYWORDS
    )


def collect_reconnaissance(sample: str) -> dict[str, Any]:
    import_items = imports(sample)
    function_items = functions(sample)
    string_items = strings(sample)

    suspicious_imports = [
        item
        for item in import_items
        if any(
            keyword in str(item.get("name", "")).lower()
            for keyword in SUSPICIOUS_IMPORT_KEYWORDS
        )
    ][:40]

    large_functions = sorted(
        function_items,
        key=lambda item: (
            item.get("size") or 0,
            item.get("instructions") or 0,
        ),
        reverse=True,
    )[:30]

    interesting_strings = [
        {
            "value": item.get("string"),
            "address": item.get("vaddr") or item.get("paddr"),
            "section": item.get("section"),
        }
        for item in string_items
        if isinstance(item.get("string"), str)
        and _is_clean_interesting_string(item["string"])
    ][:40]

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
