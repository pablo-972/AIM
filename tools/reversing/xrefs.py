from tools.reversing.session import R2Session


def run_xrefs(sample: str, value: str) -> dict:
    with R2Session(sample) as r2:
        r2.cmd(f"s {value}")
        xrefs = r2.cmdj("axtj") or []

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
            for item in xrefs
        ],
    }


def run_string_xrefs(sample: str, string_value: str) -> dict:
    with R2Session(sample) as r2:
        strings = r2.cmdj("izj") or []
        matches = [
            item
            for item in strings
            if string_value.lower() in str(item.get("string", "")).lower()
        ]

        results = []
        for item in matches:
            address = item.get("vaddr") or item.get("paddr")
            if address is None:
                continue

            r2.cmd(f"s {address}")
            xrefs = r2.cmdj("axtj") or []

            results.append(
                {
                    "string": item.get("string"),
                    "address": address,
                    "xrefs": xrefs,
                }
            )

    return {
        "query": string_value,
        "matches": results,
    }