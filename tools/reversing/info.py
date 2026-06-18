from tools.reversing.session import R2Session


def run_info(sample: str) -> dict:
    with R2Session(sample) as r2:
        return {
            "binary_info": r2.cmdj("ij") or {},
            "entrypoints": r2.cmdj("iej") or [],
        }