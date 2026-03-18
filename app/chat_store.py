"""
Persist Telegram chat ids so the queue consumer can notify all known chats.
"""

import json
import os
from pathlib import Path
from typing import Any


def _default_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "data"


def _data_dir(data_dir: str | Path | None = None) -> Path:
    # In Docker Compose we set ANIME_DB_PATH=/app/data and mount the same volume
    return Path(data_dir or os.getenv("ANIME_DB_PATH", _default_data_dir()))


def _chat_ids_path(data_dir: str | Path | None = None) -> Path:
    return _data_dir(data_dir) / "chat_ids.json"


def load_chat_ids(data_dir: str | Path | None = None) -> list[int]:
    """Load chat ids (may be empty)."""
    path = _chat_ids_path(data_dir)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    ids: list[int] = []
    if isinstance(raw, list):
        for item in raw:
            try:
                ids.append(int(item))
            except Exception:
                continue
    return ids


def save_chat_ids(chat_ids: list[int], data_dir: str | Path | None = None) -> None:
    """Save chat ids to disk."""
    path = _chat_ids_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(chat_ids, ensure_ascii=False, indent=2), encoding="utf-8")


def add_chat_id(chat_id: int, data_dir: str | Path | None = None) -> None:
    """Add chat id if missing, then persist."""
    chat_ids = load_chat_ids(data_dir)
    if chat_id not in chat_ids:
        chat_ids.append(chat_id)
        save_chat_ids(chat_ids, data_dir)

