from __future__ import annotations

import subprocess

from app.platform.models import PlatformResult


class MacOSPermissionApi:
    def accessibility_status(self) -> PlatformResult:
        try:
            import ApplicationServices  # type: ignore

            trusted = bool(ApplicationServices.AXIsProcessTrusted())
        except Exception as exc:
            return PlatformResult(
                False,
                "无法检测辅助功能权限",
                "check_failed",
                {"status": "unknown", "platform": "macos", "error": str(exc)},
            )
        return PlatformResult(
            trusted,
            "已授权" if trusted else "未授权",
            "" if trusted else "not_authorized",
            {"status": "authorized" if trusted else "not_authorized", "platform": "macos"},
        )

    def open_accessibility_settings(self) -> PlatformResult:
        try:
            self._request_accessibility_prompt()
            urls = [
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
                "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_Accessibility",
            ]
            for url in urls:
                subprocess.Popen(["open", url])
            return PlatformResult(True, "已打开系统设置", data={"urls": urls})
        except Exception as exc:
            return PlatformResult(False, "打开系统设置失败", "open_failed", {"error": str(exc)})

    def screen_recording_status(self) -> PlatformResult:
        return PlatformResult(True, data={"status": "unknown", "platform": "macos"})

    @staticmethod
    def _request_accessibility_prompt() -> None:
        try:
            import ApplicationServices  # type: ignore

            prompt_key = getattr(
                ApplicationServices,
                "kAXTrustedCheckOptionPrompt",
                "AXTrustedCheckOptionPrompt",
            )
            request = getattr(ApplicationServices, "AXIsProcessTrustedWithOptions", None)
            if callable(request):
                request({prompt_key: True})
        except Exception:
            return
