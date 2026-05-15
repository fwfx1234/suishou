from __future__ import annotations

from pathlib import Path

from app.platform.models import AppEntry, PlatformResult


class NoopExternalLauncher:
    def launch_app(self, app: AppEntry | dict) -> PlatformResult:
        del app
        return PlatformResult(False, "当前平台不支持", "unsupported")

    def launch_system_action(self, action: str) -> PlatformResult:
        del action
        return PlatformResult(False, "当前平台不支持", "unsupported")

    def open_path(self, path: str | Path) -> PlatformResult:
        del path
        return PlatformResult(False, "当前平台不支持", "unsupported")

    def reveal_in_file_manager(self, path: str | Path) -> PlatformResult:
        del path
        return PlatformResult(False, "当前平台不支持", "unsupported")

    def open_url(self, url: str) -> PlatformResult:
        del url
        return PlatformResult(False, "当前平台不支持", "unsupported")
