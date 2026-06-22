from typing import Any

from tools.reversing.analyzers.session import R2Session


def binary_info(sample: str) -> dict[str, Any]:
    with R2Session(sample) as r2:
        return {
            "binary_info": r2.cmdj("ij") or {},
            "entrypoints": r2.cmdj("iej") or [],
        }


def imports(sample: str) -> list[dict[str, Any]]:
    with R2Session(sample) as r2:
        items = r2.cmdj("iij") or []

    return [
        {
            "name": item.get("name"),
            "plt": item.get("plt"),
            "ordinal": item.get("ordinal"),
            "bind": item.get("bind"),
            "type": item.get("type"),
            "libname": item.get("libname"),
        }
        for item in items
    ]


def functions(sample: str) -> list[dict[str, Any]]:
    with R2Session(sample) as r2:
        items = r2.cmdj("aflj") or []

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
        for item in items
    ]


def strings(sample: str) -> list[dict[str, Any]]:
    with R2Session(sample) as r2:
        items = r2.cmdj("izj") or []

    return [
        {
            "string": item.get("string"),
            "vaddr": item.get("vaddr"),
            "paddr": item.get("paddr"),
            "size": item.get("size"),
            "section": item.get("section"),
            "type": item.get("type"),
        }
        for item in items
    ]


def callers(sample: str, function: str) -> dict[str, Any]:
    if not function:
        raise ValueError("function is required")

    with R2Session(sample) as r2:
        r2.cmd(f"s {function}")
        items = r2.cmdj("axtj") or []

    return {
        "function": function,
        "callers": [
            {
                "from": item.get("from"),
                "to": item.get("to"),
                "type": item.get("type"),
                "opcode": item.get("opcode"),
                "function": item.get("fcn_name"),
            }
            for item in items
        ],
    }


def callees(sample: str, function: str) -> dict[str, Any]:
    if not function:
        raise ValueError("function is required")

    with R2Session(sample) as r2:
        r2.cmd(f"s {function}")
        function_info = r2.cmdj("pdfj") or {}

    return {
        "function": function,
        "callees": [
            {
                "offset": op.get("offset"),
                "opcode": op.get("opcode"),
                "jump": op.get("jump"),
                "ptr": op.get("ptr"),
                "callee": op.get("disasm"),
            }
            for op in function_info.get("ops", [])
            if op.get("type") in {"call", "ucall", "icall"}
        ],
    }



