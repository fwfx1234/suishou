from __future__ import annotations

from unittest.mock import patch

from app.platform.macos.notifications import MacOSNotificationApi
from app.platform.noop.notifications import NoopNotificationApi
from app.platform.windows.notifications import WindowsNotificationApi


def test_noop_notification_returns_false() -> None:
    assert NoopNotificationApi().notify(title="t", body="b") is False


def test_macos_notification_invokes_osascript_with_subtitle() -> None:
    with patch("app.platform.macos.notifications.subprocess.Popen") as popen:
        ok = MacOSNotificationApi().notify(title="标题", body="内容", success=True)
    assert ok is True
    args = popen.call_args.args[0]
    assert args[0] == "osascript"
    assert args[1] == "-e"
    script = args[2]
    assert "display notification" in script
    assert "标题" in script
    assert "内容" in script
    assert "成功" in script


def test_macos_notification_escapes_quotes_and_backslashes() -> None:
    with patch("app.platform.macos.notifications.subprocess.Popen") as popen:
        MacOSNotificationApi().notify(title='a"b\\c', body='x"y')
    script = popen.call_args.args[0][2]
    assert 'a\\"b\\\\c' in script
    assert 'x\\"y' in script


def test_macos_notification_without_success_omits_subtitle() -> None:
    with patch("app.platform.macos.notifications.subprocess.Popen") as popen:
        MacOSNotificationApi().notify(title="标题", body="内容")
    script = popen.call_args.args[0][2]
    assert "subtitle" not in script


def test_macos_notification_returns_false_when_osascript_missing() -> None:
    with patch("app.platform.macos.notifications.subprocess.Popen", side_effect=OSError):
        ok = MacOSNotificationApi().notify(title="x", body="y")
    assert ok is False


def test_windows_notification_returns_false_without_tray() -> None:
    assert WindowsNotificationApi().notify(title="t", body="b") is False


def test_windows_notification_uses_tray_show_message() -> None:
    api = WindowsNotificationApi()
    calls: list[tuple[str, str]] = []

    class FakeTray:
        def showMessage(self, title: str, body: str) -> None:
            calls.append((title, body))

    api.set_tray(FakeTray())
    ok = api.notify(title="标题", body="内容")
    assert ok is True
    assert calls == [("标题", "内容")]
