from tools.reversing.session import R2Session


def run_disasm(sample: str, function: str) -> dict:
    with R2Session(sample) as r2:
        r2.cmd(f"s {function}")

        function_info = r2.cmdj("afij") or []
        instructions = r2.cmdj("pdfj") or {}

    return {
        "function": function,
        "function_info": function_info[0] if function_info else {},
        "instructions": instructions.get("ops", []),
    }