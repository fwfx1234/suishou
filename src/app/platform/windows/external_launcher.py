from __future__ import annotations

import os
import subprocess
from pathlib import Path

from app.platform.models import AppEntry, PlatformResult


class WindowsExternalLauncher:
    def launch_app(self, app: AppEntry | dict) -> PlatformResult:
        launch_path = _launch_path_from_app(app)
        if not launch_path:
            return PlatformResult(False, "应用路径为空", "invalid")
        if not Path(launch_path).exists():
            return PlatformResult(False, "应用路径不存在", "not_found")
        try:
            os.startfile(launch_path)
            return PlatformResult(True, data={"launchPath": launch_path})
        except Exception as exc:
            return PlatformResult(False, str(exc), "failed")

    def launch_system_action(self, action: str) -> PlatformResult:
        try:
            subprocess.Popen(action, shell=True)
            return PlatformResult(True, data={"action": action})
        except Exception as exc:
            return PlatformResult(False, str(exc), "failed")

    def open_path(self, path: str | Path) -> PlatformResult:
        raw = str(path)
        if not Path(raw).exists():
            return PlatformResult(False, "路径不存在", "not_found")
        try:
            os.startfile(raw)
            return PlatformResult(True, data={"path": raw})
        except Exception as exc:
            return PlatformResult(False, str(exc), "failed")

    def reveal_in_file_manager(self, path: str | Path) -> PlatformResult:
        raw = str(path)
        if not Path(raw).exists():
            return PlatformResult(False, "路径不存在", "not_found")
        try:
            subprocess.Popen(["explorer.exe", "/select,", raw])
            return PlatformResult(True, data={"path": raw})
        except Exception as exc:
            return PlatformResult(False, str(exc), "failed")

    def open_url(self, url: str) -> PlatformResult:
        try:
            os.startfile(url)
            return PlatformResult(True, data={"url": url})
        except Exception as exc:
            return PlatformResult(False, str(exc), "failed")


def _launch_path_from_app(app: AppEntry | dict) -> str:
    if isinstance(app, AppEntry):
        return app.launch_path
    return str(app.get("launchPath") or "")
