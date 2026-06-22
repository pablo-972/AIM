from typing import Any

from tools.reversing.analyzers.session import R2Session


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
        f"{op.get('address'):#x}: {op.get('disasm')}"
        for op in selected_ops
        if op.get("address") is not None and op.get("disasm")
    )

    return {
        "function": function,
        "function_info": details["info"],
        "instructions_count": len(ops),
        "returned_instructions": len(selected_ops),
        "truncated": len(ops) > max_instructions,
        "disassembly": text,
    }