from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from app.services.clipboard.models import ClipboardItemDraft


ClipboardChangeHandler = Callable[[ClipboardItemDraft], None]


class ClipboardBackend(Protocol):
    def start(self, on_change: ClipboardChangeHandler) -> None:
        ...

    def stop(self) -> None:
        ...

    def read_current(self) -> ClipboardItemDraft | None:
        ...

    def write_text(self, text: str) -> None:
        ...

    def write_files(self, paths: list[str]) -> None:
        ...

    def write_image(self, path: str | Path) -> None:
        ...

    def clear(self) -> None:
        ...
