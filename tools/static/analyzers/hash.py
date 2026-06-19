import hashlib

import pefile


def _calc_hash(sample: str, algo: str) -> str:
    h = hashlib.new(algo)

    with open(sample, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)

    return h.hexdigest()


def _is_pe(sample: str) -> bool:
    try:
        pefile.PE(sample)
        return True
    except pefile.PEFormatError:
        return False


def calculate_md5(sample: str) -> str:
    return _calc_hash(sample, "md5")


def calculate_sha1(sample: str) -> str:
    return _calc_hash(sample, "sha1")


def calculate_sha256(sample: str) -> str:
    return _calc_hash(sample, "sha256")


def calculate_imphash(sample: str) -> str | None:
    if _is_pe(sample):
        pe = pefile.PE(sample)
        imphash = pe.get_imphash()
        return imphash if isinstance(imphash, str) else None
    else:
        return None


def calculate_hashes(sample: str) -> dict[str, str]:
    hashes: dict[str, str] = {
        "md5": calculate_md5(sample),
        "sha1": calculate_sha1(sample),
        "sha256": calculate_sha256(sample) 
    }
    
    imphash = calculate_imphash(sample)
    if imphash:
        hashes["imphash"] = imphash

    return hashes
