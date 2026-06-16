import os
import json
from datetime import datetime, timezone

from utils.io.files import save_json


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_existing_blocks(path: str, filename: str) -> dict:
    output_path = os.path.join(path, filename)
    try:
        with open(output_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, ValueError):
        return {
            "schema_version": "1.0",
            "artifact_type": "threat_actor_messages",
            "source": "static_agent",
            "items": [],
        }


def save_threat_actor_messages(path: str, filename: str, parameters: dict) -> dict:
    message_block = parameters.get("message_block")
    if not message_block:
        return {
            "saved_count": 0,
            "items": [],
        }

    data = _load_existing_blocks(path, filename)
    items = data.setdefault("items", [])
    item = {
        "id": len(items) + 1,
        "created_at": _now_iso(),
        "chunk_index": parameters.get("chunk_index"),
        "message_block": message_block,
    }

    if item["message_block"] not in [
        existing.get("message_block")
        for existing in items
    ]:
        items.append(item)

    save_json(path, filename, data)

    return {
        "saved_count": len(items),
        "item": item,
    }

