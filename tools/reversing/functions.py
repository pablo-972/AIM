from tools.reversing.session import R2Session


def run_functions(sample: str) -> list[dict]:
    with R2Session(sample) as r2:
        functions = r2.cmdj("aflj") or []

    return [
        {
            "name": item.get("name"),
            "offset": item.get("offset"),
            "size": item.get("size"),
            "realsz": item.get("realsz"),
            "noreturn": item.get("noreturn"),
            "calltype": item.get("calltype"),
            "nbbs": item.get("nbbs"),
            "nins": item.get("nins"),
        }
        for item in functions
    ]