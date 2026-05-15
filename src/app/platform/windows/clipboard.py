from __future__ import annotations

from pathlib import Path

from app.platform.models import PlatformResult
from app.services.clipboard.backends.win32_backend import Win32ClipboardBackend


class WindowsClipboardApi:
    def __init__(self, backend: Win32ClipboardBackend | None = None) -> None:
        self._backend = backend or Win32ClipboardBackend()

    def read_text(self) -> str:
        return self._backend.read_text()

    def write_text(self, text: str) -> PlatformResult:
        try:
            self._backend.write_text(text)
        except Exception as exc:
            return PlatformResult(False, str(exc), "failed")
        return PlatformResult(True, data={"type": "text"})

    def clear(self) -> PlatformResult:
        try:
            self._backend.clear()
        except Exception as exc:
            return PlatformResult(False, str(exc), "failed")
        return PlatformResult(True)

    def write_files(self, paths: list[str | Path]) -> PlatformResult:
        clean_paths = [Path(path) for path in paths if str(path)]
        if not clean_paths:
            return PlatformResult(False, "文件列表为空", "invalid")
        missing = [str(path) for path in clean_paths if not path.exists()]
        if missing:
            return PlatformResult(False, "文件不存在", "not_found", {"missing": missing})
        try:
            self._backend.write_files([str(path) for path in clean_paths])
        except Exception as exc:
            return PlatformResult(False, str(exc), "failed")
        return PlatformResult(True, data={"type": "files", "count": len(clean_paths)})
