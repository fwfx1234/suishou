from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


ClipboardItemType = Literal["text", "image", "files"]


DEFAULT_CLIPBOARD_CONFIG = {
    "capture_text": True,
    "capture_image": True,
    "capture_files": True,
    "max_text_chars": 20000,
    "ignore_patterns": [],
    "hotkey": "Alt+V",
}


@dataclass(slots=True)
class ClipboardItemDraft:
    item_type: ClipboardItemType
    content: str = ""
    preview: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    image_bytes: bytes | None = None
