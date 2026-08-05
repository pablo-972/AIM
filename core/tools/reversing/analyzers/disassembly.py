from typing import Any

from core.tools.reversing.analyzers.functions import resolve_code_target
from core.tools.reversing.analyzers.session import R2Session
from core.utils.postprocessing.reversing.functions import target_reference


def disassembly(
    sample: str,
    address: str | None = None,
    function: str | None = None,
) -> dict[str, Any]:
    details = _function_analysis(sample, address, function)

    return {
        **target_reference(address, function),
        "resolved_function": details["resolved_function"],
        "function_info": details["info"],
        "instructions_count": len(details["instructions"]),
        "start_address": details["start_address"],
        "end_address": details["end_address"],
        "instructions": details["instructions"],
    }


def _function_analysis(
    sample: str,
    address: str | None,
    function: str | None,
) -> dict[str, Any]:
    with R2Session(sample) as r2:
        resolved_function = resolve_code_target(r2, address, function)

        info = r2.cmdj(f"afij @ {resolved_function}") or []
        disasm = r2.cmdj(f"pdfj @ {resolved_function}") or {}

    instructions = []
    for op in disasm.get("ops", []):
        instruction = {
            "address": op.get("addr") or op.get("offset"),
            "type": op.get("type"),
            "opcode": op.get("opcode"),
            "disasm": op.get("disasm"),
            "size": op.get("size"),
            "bytes": op.get("bytes"),
            "jump": op.get("jump"),
            "fail": op.get("fail"),
            "ptr": op.get("ptr"),
            "refptr": op.get("refptr"),
            "refs": op.get("refs", []),
        }

        instructions.append(instruction)

    addresses = []
    for instruction in instructions:
        address = instruction.get("address")

        if isinstance(address, int):
            addresses.append(address)

    start_address = None
    end_address = None
    if addresses:
        start_address = hex(min(addresses))
        end_address = hex(max(addresses))


    return {
        "resolved_function": resolved_function,
        "info": info[0] if info else {},
        "instructions": instructions,
        "start_address": start_address,
        "end_address": end_address,
    }


# def text_disassembly(
#     sample: str,
#     function: str,
# ) -> dict[str, Any]:
#     details = _function_analysis(sample, function)
#     ops = details["instructions"]

#     text_lines = []
#     addresses = []  

#     for op in ops:
#         address = op.get("address")
#         disasm = op.get("disasm")

#         if address is not None and disasm:
#             text_lines.append(f"{address:#x}: {disasm}")

#         if isinstance(address, int):
#             addresses.append(address)

#     text = "\n".join(text_lines)

#     if addresses:
#         start_address = hex(min(addresses))
#         end_address = hex(max(addresses))
#     else:
#         start_address = details["start_address"]
#         end_address = details["end_address"]

#     return {
#         "function": function,
#         "resolved_function": details["resolved_function"],
#         "function_info": details["info"],
#         "instructions_count": len(ops),
#         "returned_instructions": len(ops),
#         "start_address": start_address,
#         "end_address": end_address,
#         "disassembly": text,
#     }
