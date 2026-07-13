from typing import Any

from core.tools.reversing.analyzers.session import R2Session


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
            "libname": item.get("libname"),
            "type": item.get("type"),
            "ordinal": item.get("ordinal"),
            "bind": item.get("bind"),
            "plt": item.get("plt"),
        }
        for item in items
    ]


def functions(sample: str) -> list[dict[str, Any]]:
    with R2Session(sample) as r2:
        items = r2.cmdj("aflj") or []

    return [
        {
            "name": item.get("name"),
            "address": item.get("addr"),
            "type": item.get("type"),
            "signature": item.get("signature"),
            "size": item.get("size"),
            "realsz": item.get("realsz"),
            "instructions": item.get("ninstrs"),
            "basic_blocks": item.get("nbbs"),
            "edges": item.get("edges"),
            "calltype": item.get("calltype"),
            "nargs": item.get("nargs"),
            "nlocals": item.get("nlocals"),
            "stackframe": item.get("stackframe"),
            "recursive": item.get("recursive"),
            "noreturn": item.get("noreturn"),
            "indegree": item.get("indegree"),
            "outdegree": item.get("outdegree"),
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
        items = r2.cmdj(f"axtj @ {function}") or []

    return {
        "function": function,
        "callers": [
            {
                "from": item.get("from"),
                "function": item.get("fcn_name"),
                "to": item.get("to"),
                "type": item.get("type"),
                "opcode": item.get("opcode"),
                "perm": item.get("perm"),
            }
            for item in items
        ],
    }


def callees(sample: str, function: str) -> dict[str, Any]:
    if not function:
        raise ValueError("function is required")

    with R2Session(sample) as r2:
        function_info = r2.cmdj(f"pdfj @ {function}") or {}

    calls = []
    for op in function_info.get("ops", []):
        if op.get("type") in {"call", "ucall", "icall"}:
            calls.append(op)

    return {
        "function": function,
        "callees": [
            {
                "call_address": op.get("addr") or op.get("offset"),
                "call_type": op.get("type"),
                "opcode": op.get("opcode"),
                "disasm": op.get("disasm"),
                "target_address": op.get("jump") or op.get("ptr"),
                "fallthrough": op.get("fail"),
                "refs": op.get("refs", []),
            }
            for op in calls
        ],
        "count": len(calls),
    }



