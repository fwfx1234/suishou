from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.paths import MacOSAppPaths, NoopAppPaths, WindowsAppPaths


def test_macos_user_data_dir_uses_library_application_support() -> None:
    paths = MacOSAppPaths()
    expected = Path.home() / "Library" / "Application Support" / "PyDesktopTools"
    assert paths.user_data_dir() == expected


def test_windows_user_data_dir_uses_appdata(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.delenv("PY_DESKTOP_TOOLS_DATA_DIR", raising=False)
    paths = WindowsAppPaths()
    assert paths.user_data_dir() == tmp_path / "PyDesktopTools"


def test_noop_user_data_dir_uses_local_share() -> None:
    paths = NoopAppPaths()
    expected = Path.home() / ".local" / "share" / "py-desktop-tools"
    assert paths.user_data_dir() == expected


def test_data_dir_env_var_overrides_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PY_DESKTOP_TOOLS_DATA_DIR", str(tmp_path / "custom"))
    paths = MacOSAppPaths()
    assert paths.user_data_dir() == tmp_path / "custom"


def test_feature_output_dir_preserves_case() -> None:
    paths = MacOSAppPaths()
    assert paths.feature_output_dir("QR") == Path.home() / "Downloads" / "PyDesktopTools" / "QR"
    assert paths.feature_output_dir("Downloads") == Path.home() / "Downloads" / "PyDesktopTools" / "Downloads"


def test_windows_downloads_uses_user_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    paths = WindowsAppPaths()
    assert paths.downloads_dir() == tmp_path / "Downloads"
    assert paths.desktop_dir() == tmp_path / "Desktop"
    assert paths.documents_dir() == tmp_path / "Documents"


def test_plugin_dirs_uses_pathsep_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    monkeypatch.setenv("PY_DESKTOP_TOOLS_PLUGIN_DIR", os.pathsep.join([str(a), str(b)]))
    paths = MacOSAppPaths()
    assert paths.plugin_dirs() == [a, b]


def test_plugin_dirs_falls_back_to_project_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PY_DESKTOP_TOOLS_PLUGIN_DIR", raising=False)
    paths = MacOSAppPaths()
    dirs = paths.plugin_dirs()
    assert len(dirs) == 1
    assert dirs[0].name == "plugins"


def test_cache_dir_is_subdir_of_user_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PY_DESKTOP_TOOLS_DATA_DIR", str(tmp_path))
    paths = NoopAppPaths()
    cache = paths.cache_dir()
    assert cache == tmp_path / "cache"
    assert cache.exists()
