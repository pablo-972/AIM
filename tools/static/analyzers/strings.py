import re

from exceptions import ToolError
from utils.io.commands import run_command


IP_REGEX = re.compile(
    r"(?<![\w.])(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?![\w.])"
)


URL_REGEX = re.compile(
    r"\b(?:https?|hxxps?|ftp)://[^\s\"'<>]{4,}",
    re.IGNORECASE,
)


DOMAIN_REGEX = re.compile(
    r"(?<![@\w-])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"(?:com|net|org|ru|cn|co|io|xyz|top|gov|biz|info|su|onion|"
    r"site|online|click|club|vip|cc|tv|me|dev|app|shop|live|icu|pw|"
    r"tk|ml|ga|cf|gq|de|uk|fr|es|it|nl|pl|br|in|jp|kr)(?![\w-])",
    re.IGNORECASE,
)


REGISTRY_REGEX = re.compile(
    r"\b(?:HKEY_CLASSES_ROOT|HKEY_CURRENT_USER|HKEY_LOCAL_MACHINE|"
    r"HKEY_USERS|HKEY_CURRENT_CONFIG|HKCR|HKCU|HKLM|HKU|HKCC)"
    r"\\[A-Za-z0-9_ .${}\\/-]+",
    re.IGNORECASE,
)


FILE_NAME_REGEX = re.compile(
    r"^[\w .()+-]+\.(?:dll|exe|sys|pdb|obj|lib|ini|dat|tmp|log|"
    r"cab|mui|manifest|cat|msi|bin|json|xml|png|jpg|ico)$",
    re.IGNORECASE,
)


EMAIL_REGEX = re.compile(
    r"(?<![\w.+-])[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,24}(?![\w.-])"
)


PATH_REGEX = re.compile(
    r"(?:[A-Za-z]:\\(?:[^\\\n]+\\)*[^\\\n]*"          # C:\...
    r"|(?:\.\.|[A-Za-z0-9_\-\.]+)\\(?:[^\\\n]+\\)*[^\\\n]*)"  # Relative routes
)


BTC_REGEX = re.compile(r"\b(?:bc1[ac-hj-np-z02-9]{11,71}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b")
BCH_REGEX = re.compile(r"\b(?:bitcoincash:)?(?:q|p)[a-z0-9]{41}\b", re.IGNORECASE)
XMR_REGEX = re.compile(r"\b(?:4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}|8[1-9A-HJ-NP-Za-km-z]{94})\b")
ETH_REGEX = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
LTC_REGEX = re.compile(r"\b(?:ltc1[ac-hj-np-z02-9]{11,71}|[LM3][a-km-zA-HJ-NP-Z1-9]{26,33})\b")


def get_raw_strings(sample: str) -> list[str]:
    result = run_command(["strings", str(sample)])
    if result.timed_out:
        raise ToolError("strings command timed out")
    if not result.ok:
        raise ToolError(result.stderr or f"strings failed with code {result.returncode}")

    strings = result.stdout.splitlines()
    return strings


def parse_strings(strings: list[str]) -> list[str]:
    parsed_strings: list[str] = []
    for string in strings:
        if not is_noise(string):
            parsed_strings.append(string)
    return parsed_strings


def find_regex(strings: list[str], regex: re.Pattern[str]) -> list[str]:
    matches: list[str] = []
    for string in strings:
        matches.extend(match.group(0) for match in regex.finditer(string))
    return list(dict.fromkeys(matches))


def get_ips(strings: list[str]) -> list[str]:
    return find_regex(strings, IP_REGEX)


def get_urls(strings: list[str]) -> list[str]:
    return find_regex(strings, URL_REGEX)


def get_domains(strings: list[str]) -> list[str]:
    return find_regex(strings, DOMAIN_REGEX)


def get_registry_keys(strings: list[str]) -> list[str]:
    return find_regex(strings, REGISTRY_REGEX)


def get_file_names(strings: list[str]) -> list[str]:
    return find_regex(strings, FILE_NAME_REGEX)


def get_emails(strings: list[str]) -> list[str]:
    return find_regex(strings, EMAIL_REGEX)


def get_crypto_wallets(strings: list[str]) -> dict[str, list[str]]:
    return {
        "btc": find_regex(strings, BTC_REGEX),
        "bch": find_regex(strings, BCH_REGEX),
        "xmr": find_regex(strings, XMR_REGEX),
        "eth": find_regex(strings, ETH_REGEX),
        "ltc": find_regex(strings, LTC_REGEX),
    }


def is_noise(string: str) -> bool:
    # Only caps
    if re.fullmatch(r"[A-Z]{1,}", string):
        return True

    # Hex shellcode
    if re.fullmatch(r"[A-F0-9]{16,}", string):
        return True

    # No vowels
    if 3 <= len(string) <= 8 and not re.search(r"[aeiouAEIOU]", string):
        return True

    # Same character repeated
    if len(set(string)) == 1:
        return True

    # Rare symbols
    symbol_ratio = len(re.findall(r"[^A-Za-z0-9\s.:/_\\-]", string)) / max(1, len(string))
    if symbol_ratio > 0.3:
        return True

    # Very long with no spaces
    if len(string) > 120 and " " not in string:
        return True
    
    # Very short with no spaces
    if len(string) < 7:
        return True

    # GUID format
    if re.fullmatch(r"[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}", string):
        return True

    # Timestamps
    if re.match(r"\d{4}-\d{2}-\d{2}", string):
        return True

    # Log prefixes
    if re.match(r"(INFO|DEBUG|WARN|ERROR|TRACE)", string, flags=re.IGNORECASE):
        return True

    # Large numeric garbage
    if re.fullmatch(r"\d{6,}", string):
        return True

    # dll/exe names that are not suspicious imports
    if string.lower().endswith((".dll", ".exe")):
        if not any(k in string.lower() for k in ["crypt", "net", "win", "inject"]):
            return True
        
    # Compilation paths
    if PATH_REGEX.search(string):
        return True

    return False



def analyze_strings(sample: str) -> dict[str, object]:
    raw_strings = get_raw_strings(sample)
    parsed_strings = parse_strings(raw_strings)

    return {
        "parsed_strings": parsed_strings,
        "ips": get_ips(raw_strings),
        "urls": get_urls(raw_strings),
        "domains": get_domains(raw_strings),
        "registry_keys": get_registry_keys(raw_strings),
        "file_names": get_file_names(raw_strings),
        "emails": get_emails(raw_strings),
        "crypto_wallets": get_crypto_wallets(raw_strings),
    }
