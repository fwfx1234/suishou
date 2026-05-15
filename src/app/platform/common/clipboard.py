from __future__ import annotations

from pathlib import Path

from app.platform.models import PlatformResult
from app.services.clipboard.backends.pyperclip_backend import PyperclipClipboardBackend


class PyperclipClipboardApi:
    def __init__(self, backend: PyperclipClipboardBackend | None = None) -> None:
        self._backend = backend or PyperclipClipboardBackend()

    def read_text(self) -> str:
        return self._backend.read_text()

    def write_text(self, text: str) -> PlatformResult:
        try:
            self._backend.write_text(text)
        except Exception as exc:
            return PlatformResult(False, str(exc), "failed")
        return PlatformResult(True, data={"type": "text"})

    def write_files(self, paths: list[str | Path]) -> PlatformResult:
        del paths
        return PlatformResult(False, "当前平台剪贴板暂不支持文件写入", "unsupported")

    def clear(self) -> PlatformResult:
        try:
            self._backend.clear()
        except Exception as exc:
            return PlatformResult(False, str(exc), "failed")
        return PlatformResult(True)
