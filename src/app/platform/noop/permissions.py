from __future__ import annotations

from app.platform.models import PlatformResult


class NoopPermissionApi:
    def accessibility_status(self) -> PlatformResult:
        return PlatformResult(False, "当前平台不支持", "unsupported", {"status": "unsupported"})

    def open_accessibility_settings(self) -> PlatformResult:
        return PlatformResult(False, "当前平台不支持", "unsupported")

    def screen_recording_status(self) -> PlatformResult:
        return PlatformResult(False, "当前平台不支持", "unsupported", {"status": "unsupported"})
