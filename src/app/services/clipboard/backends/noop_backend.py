from __future__ import annotations

from pathlib import Path


class NoopClipboardBackend:
    def start(self, on_change) -> None:
        del on_change
        return

    def stop(self) -> None:
        return

    def read_current(self):
        return None

    def write_text(self, text: str) -> None:
        del text
        raise RuntimeError("当前平台不支持剪贴板")

    def write_files(self, paths: list[str]) -> None:
        del paths
        raise RuntimeError("当前平台不支持剪贴板")

    def write_image(self, path: str | Path) -> None:
        del path
        raise RuntimeError("当前平台不支持剪贴板")

    def clear(self) -> None:
        raise RuntimeError("当前平台不支持剪贴板")
