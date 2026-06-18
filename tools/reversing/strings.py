from tools.reversing.session import R2Session


def run_reversing_strings(sample: str) -> list[dict]:
    with R2Session(sample) as r2:
        strings = r2.cmdj("izj") or []

    return [
        {
            "string": item.get("string"),
            "vaddr": item.get("vaddr"),
            "paddr": item.get("paddr"),
            "size": item.get("size"),
            "section": item.get("section"),
            "type": item.get("type"),
        }
        for item in strings
    ]