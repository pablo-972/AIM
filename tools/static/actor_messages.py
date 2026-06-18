import json
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

from utils.io.files import save_json


DEFAULT_ARTIFACT = {
    "artifact_type": "threat_actor_messages",
    "source": "static_agent",
    "items": [],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_artifact() -> dict[str, Any]:
    return {
        **DEFAULT_ARTIFACT,
        "items": [],
    }


def _load_existing_blocks(path: str, filename: str) -> dict[str, Any]:
    output_path = Path(path) / filename
    try:
        with output_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        
        if isinstance(data, dict):
            data.setdefault("items", [])
            return data
    except (OSError, json.JSONDecodeError):
        pass

    return _default_artifact()


def _message_exists(items: list[dict[str, Any]], message_block: str) -> bool:
    return any(
        item.get("message_block") == message_block
        for item in items
    )


def save_threat_actor_messages(path: str, filename: str, parameters: dict[str, list[str]]) -> dict[str, Any]:
    message_block = parameters.get("message_block")
    if not isinstance(message_block, str) or not message_block.strip():
        return {
            "success": False,
            "saved": False,
            "reason": "missing_message_block",
            "saved_count": 0,
        }

    data = _load_existing_blocks(path, filename)
    items = data.setdefault("items", [])

    if _message_exists(items, message_block):
        save_json(path, filename, data)
        return {
            "success": True,
            "saved": False,
            "reason": "duplicate",
            "saved_count": len(items),
        }

    item = {
        "id": len(items) + 1,
        "created_at": _now_iso(),
        "chunk_index": parameters.get("chunk_index"),
        "message_block": message_block,
    }

    items.append(item)
    save_json(path, filename, data)

    return {
        "success": True,
        "saved": True,
        "saved_count": len(items),
        "item": item,
    }

