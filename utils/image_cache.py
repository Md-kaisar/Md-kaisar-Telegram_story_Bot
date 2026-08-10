"""
Lightweight in-memory cache mapping a short image key -> raw bytes / telegram file_id /
cached scene description. Keeps callback_data small (Telegram limits it to 64 bytes) and
avoids re-running Gemini Vision every time a user picks a different action for the same photo.

Bounded size with simple LRU eviction so long-running bots don't leak memory.
"""
from collections import OrderedDict
import uuid

_MAX_ENTRIES = 500
_store: "OrderedDict[str, dict]" = OrderedDict()


def new_key() -> str:
    return uuid.uuid4().hex[:10]


def put(key: str, *, image_bytes: bytes, file_id: str, mime_type: str = "image/jpeg"):
    _store[key] = {
        "image_bytes": image_bytes,
        "file_id": file_id,
        "mime_type": mime_type,
        "scene": None,
    }
    _store.move_to_end(key)
    while len(_store) > _MAX_ENTRIES:
        _store.popitem(last=False)


def get(key: str) -> dict | None:
    entry = _store.get(key)
    if entry:
        _store.move_to_end(key)
    return entry


def set_scene(key: str, scene: str):
    if key in _store:
        _store[key]["scene"] = scene
