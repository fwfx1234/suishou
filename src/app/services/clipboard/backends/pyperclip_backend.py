from __future__ import annotations

import time
from pathlib import Path
from threading import Event, Thread

from app.services.clipboard.models import ClipboardItemDraft


class PyperclipClipboardBackend:
    def __init__(self, *, poll_interval: float = 0.35) -> None:
        self._poll_interval = max(0.1, float(poll_interval))
        self._callback = None
        self._thread: Thread | None = None
        self._stop_event = Event()
        self._last_text = ""
        self._suppress_text = ""

    def start(self, on_change) -> None:
        self._callback = on_change
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._last_text = self.read_text()
        self._thread = Thread(
            target=self._poll_loop,
            name="clipboard-pyperclip-listener",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._thread = None
        self._callback = None

    def read_current(self) -> ClipboardItemDraft | None:
        text = self.read_text()
        if not text:
            return None
        return ClipboardItemDraft(
            item_type="text",
            content=text,
            preview=_compact_preview(text),
        )

    def read_text(self) -> str:
        try:
            return str(_pyperclip().paste() or "")
        except Exception:
            return ""

    def write_text(self, text: str) -> None:
        _pyperclip().copy(text or "")
        self._suppress_text = text or ""
        self._last_text = text or ""

    def write_files(self, paths: list[str]) -> None:
        del paths
        raise RuntimeError("当前平台剪贴板暂不支持文件写入")

    def write_image(self, path: str | Path) -> None:
        del path
        raise RuntimeError("当前平台剪贴板暂不支持图片写入")

    def clear(self) -> None:
        _pyperclip().copy("")
        self._suppress_text = ""
        self._last_text = ""

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            text = self.read_text()
            if text != self._last_text:
                self._last_text = text
                if text and text != self._suppress_text and callable(self._callback):
                    self._callback(
                        ClipboardItemDraft(
                            item_type="text",
                            content=text,
                            preview=_compact_preview(text),
                        )
                    )
                if text == self._suppress_text:
                    self._suppress_text = ""
            self._stop_event.wait(self._poll_interval)


def _compact_preview(text: str, limit: int = 160) -> str:
    preview = " ".join(text.replace("\r", " ").replace("\n", " ").split())
    if len(preview) > limit:
        return preview[: limit - 3] + "..."
    return preview


def _pyperclip():
    try:
        import pyperclip
    except Exception as exc:
        raise RuntimeError("pyperclip 不可用，当前平台剪贴板文本能力不可用") from exc
    return pyperclip
