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


def function_details(sample: str, function: str) -> dict[str, Any]:
    if not function:
        raise ValueError("function is required")

    with R2Session(sample) as r2:
        r2.cmd(f"s {function}")
        info = r2.cmdj("afij") or []
        disasm = r2.cmdj("pdfj") or {}

    return {
        "function": function,
        "info": info[0] if info else {},
        "instructions": disasm.get("ops", []),
    }


def disassembly(sample: str, function: str) -> dict[str, Any]:
    details = function_details(sample, function)
    return {
        "function": details["function"],
        "function_info": details["info"],
        "instructions": details["instructions"],
    }


def text_disassembly(sample: str, function: str, max_instructions: int = 300) -> dict[str, Any]:
    details = function_details(sample, function)
    ops = details["instructions"]
    selected_ops = ops[:max_instructions]
    text = "\n".join(
        f"{op.get('offset'):#x}: {op.get('disasm')}"
        for op in selected_ops
        if op.get("offset") is not None and op.get("disasm")
    )

    return {
        "function": function,
        "function_info": details["info"],
        "instructions_count": len(ops),
        "returned_instructions": len(selected_ops),
        "truncated": len(ops) > max_instructions,
        "disassembly": text,
    }


def xrefs(sample: str, value: str) -> dict[str, Any]:
    if not value:
        raise ValueError("value is required")

    with R2Session(sample) as r2:
        r2.cmd(f"s {value}")
        items = r2.cmdj("axtj") or []

    return {
        "target": value,
        "xrefs": [
            {
                "from": item.get("from"),
                "to": item.get("to"),
                "type": item.get("type"),
                "opcode": item.get("opcode"),
                "fcn_name": item.get("fcn_name"),
            }
            for item in items
        ],
    }


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


def string_xrefs(sample: str, value: str, include_all_strings: bool = False) -> dict[str, Any]:
    if not value:
        raise ValueError("value is required")

    command = "izzj" if include_all_strings else "izj"
    with R2Session(sample) as r2:
        items = r2.cmdj(command) or []
        matches = [
            item
            for item in items
            if value.lower() in str(item.get("string", "")).lower()
        ]

        results = []
        for item in matches:
            address = item.get("vaddr") or item.get("paddr")
            if address is None:
                continue

            r2.cmd(f"s {address}")
            results.append(
                {
                    "string": item.get("string"),
                    "address": address,
                    "section": item.get("section"),
                    "xrefs": r2.cmdj("axtj") or [],
                }
            )

    return {
        "query": value,
        "matches": results,
    }


def import_xrefs(sample: str, import_name: str) -> dict[str, Any]:
    if not import_name:
        raise ValueError("import_name is required")

    with R2Session(sample) as r2:
        items = r2.cmdj("iij") or []
        matches = [
            item
            for item in items
            if import_name.lower() in str(item.get("name", "")).lower()
        ]

        results = []
        for item in matches:
            address = item.get("plt") or item.get("vaddr") or item.get("offset")
            if address is None:
                continue

            r2.cmd(f"s {address}")
            results.append(
                {
                    "import": item.get("name"),
                    "address": address,
                    "library": item.get("libname"),
                    "xrefs": r2.cmdj("axtj") or [],
                }
            )

    return {
        "query": import_name,
        "matches": results,
    }
