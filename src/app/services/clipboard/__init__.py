from __future__ import annotations

__all__ = [
    "ClipboardHistoryStore",
    "ClipboardItemDraft",
    "ClipboardService",
    "DEFAULT_CLIPBOARD_CONFIG",
]


def __getattr__(name: str):
    if name == "ClipboardHistoryStore":
        from .history_store import ClipboardHistoryStore

        return ClipboardHistoryStore
    if name in {"ClipboardItemDraft", "DEFAULT_CLIPBOARD_CONFIG"}:
        from . import models

        return getattr(models, name)
    if name == "ClipboardService":
        from .service import ClipboardService

        return ClipboardService
    raise AttributeError(name)
