from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import patch

from app.platform.macos.permissions import MacOSPermissionApi
from app.platform.noop.permissions import NoopPermissionApi
from app.platform.windows.permissions import WindowsPermissionApi


def test_windows_accessibility_status_is_not_required() -> None:
    result = WindowsPermissionApi().accessibility_status()
    assert result.ok is True
    assert result.data["status"] == "not_required"


def test_windows_open_accessibility_settings_returns_unsupported() -> None:
    result = WindowsPermissionApi().open_accessibility_settings()
    assert result.ok is False
    assert result.error_code == "unsupported"


def test_noop_accessibility_status_unsupported() -> None:
    result = NoopPermissionApi().accessibility_status()
    assert result.ok is False
    assert result.data["status"] == "unsupported"


def test_macos_accessibility_status_authorized() -> None:
    fake = SimpleNamespace(AXIsProcessTrusted=lambda: True)
    with patch.dict(sys.modules, {"ApplicationServices": fake}):
        result = MacOSPermissionApi().accessibility_status()
    assert result.ok is True
    assert result.data["status"] == "authorized"


def test_macos_accessibility_status_unauthorized() -> None:
    fake = SimpleNamespace(AXIsProcessTrusted=lambda: False)
    with patch.dict(sys.modules, {"ApplicationServices": fake}):
        result = MacOSPermissionApi().accessibility_status()
    assert result.ok is False
    assert result.data["status"] == "not_authorized"


def test_macos_open_accessibility_settings_invokes_open() -> None:
    with patch("app.platform.macos.permissions.subprocess.Popen") as popen:
        result = MacOSPermissionApi().open_accessibility_settings()
    assert result.ok is True
    assert popen.call_count == 2
