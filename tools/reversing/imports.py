from tools.reversing.session import R2Session


def run_imports(sample: str) -> list[dict]:
    with R2Session(sample) as r2:
        imports = r2.cmdj("iij") or []

    return [
        {
            "name": item.get("name"),
            "plt": item.get("plt"),
            "ordinal": item.get("ordinal"),
            "bind": item.get("bind"),
            "type": item.get("type"),
            "libname": item.get("libname"),
        }
        for item in imports
    ]