import requests
from typing import Any

from config import get_env
from exceptions import ToolError
from tools.static.analyzers.hash import calculate_sha256

VT_TIMEOUT = 30


def get_vt_data(sample: str) -> dict[str, Any]:
    sample_hash = calculate_sha256(sample)
    return _request_vt(sample_hash)


def _request_vt(sample_hash: str) -> dict[str, Any]:
    url = f"{get_env('VT_API_BASE_URL')}/files/{sample_hash}"
    headers = {
        "x-apikey": get_env("VT_API_KEY"),
        "accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, timeout=VT_TIMEOUT)
    except requests.RequestException as exc:
        raise ToolError(f"VirusTotal request failed: {exc}") from exc

    if response.status_code == 200:
        data = response.json()
        if not isinstance(data, dict):
            raise ToolError("VirusTotal response must be a JSON object")
        
        return data

    raise ToolError(f"VirusTotal returned HTTP {response.status_code}: {response.text[:300]}")



