"""跨平台路径策略。

此模块在 PlatformServices 实例化之前就被多处 import（storage/manager.py、
logging/manager.py、app_bootstrap.py、plugins/manifest_loader.py、tray、features/system），
因此**不能**依赖 `app.platform` 树（会触发循环 import）。

类定义放在本文件内作为单源真值，`app.platform.{macos,windows,noop}.paths` 仅作薄
re-export，供 `PlatformServices.paths` 字段使用。模块级函数兼容旧调用方。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from app.settings import configured_text


class AppPathsBase:
    DATA_DIR_ENV = "PY_DESKTOP_TOOLS_DATA_DIR"
    PLUGIN_DIR_ENV = "PY_DESKTOP_TOOLS_PLUGIN_DIR"

    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    def is_frozen(self) -> bool:
        return bool(getattr(sys, "frozen", False))

    def resource_root(self) -> Path:
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return self.project_root()

    def user_data_dir(self) -> Path:
        configured = configured_text("paths.dataDir", self.DATA_DIR_ENV).strip()
        if configured:
            root = Path(configured).expanduser()
        else:
            root = self._default_user_data_dir()
        root.mkdir(parents=True, exist_ok=True)
        return root

    def cache_dir(self) -> Path:
        root = self.user_data_dir() / "cache"
        root.mkdir(parents=True, exist_ok=True)
        return root

    def db_path(self, name: str) -> Path:
        return self.user_data_dir() / name

    def plugin_dirs(self) -> list[Path]:
        values = configured_text("paths.pluginDirs", self.PLUGIN_DIR_ENV).strip()
        if not values:
            return [self.project_root() / "plugins"]
        return [Path(item.strip()).expanduser() for item in values.split(os.pathsep) if item.strip()]

    def downloads_dir(self) -> Path:
        return Path.home() / "Downloads"

    def desktop_dir(self) -> Path:
        return Path.home() / "Desktop"

    def documents_dir(self) -> Path:
        return Path.home() / "Documents"

    def feature_output_dir(self, feature_id: str) -> Path:
        return self.downloads_dir() / "PyDesktopTools" / feature_id

    def _default_user_data_dir(self) -> Path:
        raise NotImplementedError


class MacOSAppPaths(AppPathsBase):
    def _default_user_data_dir(self) -> Path:
        return Path.home() / "Library" / "Application Support" / "PyDesktopTools"


class WindowsAppPaths(AppPathsBase):
    def _default_user_data_dir(self) -> Path:
        return Path(os.getenv("APPDATA", str(Path.home()))) / "PyDesktopTools"

    def downloads_dir(self) -> Path:
        return self._user_profile() / "Downloads"

    def desktop_dir(self) -> Path:
        return self._user_profile() / "Desktop"

    def documents_dir(self) -> Path:
        return self._user_profile() / "Documents"

    @staticmethod
    def _user_profile() -> Path:
        profile = os.getenv("USERPROFILE", "").strip()
        if profile:
            return Path(profile)
        return Path.home()


class NoopAppPaths(AppPathsBase):
    def _default_user_data_dir(self) -> Path:
        return Path.home() / ".local" / "share" / "py-desktop-tools"


_default_paths: AppPathsBase | None = None


def _get_paths() -> AppPathsBase:
    global _default_paths
    if _default_paths is None:
        if sys.platform == "darwin":
            _default_paths = MacOSAppPaths()
        elif sys.platform == "win32":
            _default_paths = WindowsAppPaths()
        else:
            _default_paths = NoopAppPaths()
    return _default_paths


def project_root() -> Path:
    return _get_paths().project_root()


def is_frozen() -> bool:
    return _get_paths().is_frozen()


def resource_root() -> Path:
    return _get_paths().resource_root()


def user_data_dir() -> Path:
    return _get_paths().user_data_dir()


def data_dir() -> Path:
    return user_data_dir()


def db_path(name: str) -> Path:
    return _get_paths().db_path(name)


def cache_dir() -> Path:
    return _get_paths().cache_dir()


def plugin_dirs() -> list[Path]:
    return _get_paths().plugin_dirs()
