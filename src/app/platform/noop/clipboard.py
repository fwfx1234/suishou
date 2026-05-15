from __future__ import annotations

from pathlib import Path

from app.platform.models import PlatformResult


class NoopClipboardApi:
    def read_text(self) -> str:
        return ""

    def write_text(self, text: str) -> PlatformResult:
        del text
        return PlatformResult(False, "当前平台不支持", "unsupported")

    def write_files(self, paths: list[str | Path]) -> PlatformResult:
        del paths
        return PlatformResult(False, "当前平台不支持", "unsupported")

    def clear(self) -> PlatformResult:
        return PlatformResult(False, "当前平台不支持", "unsupported")
