from __future__ import annotations

from app.platform.noop.windowing import NoopWindowingApi


def test_noop_configure_launcher_returns_false() -> None:
    api = NoopWindowingApi()
    assert api.configure_launcher_window(object()) is False


def test_noop_configure_overlay_returns_false() -> None:
    api = NoopWindowingApi()
    assert api.configure_overlay_window(object(), force_top=True) is False


def test_noop_activate_window_returns_false() -> None:
    api = NoopWindowingApi()
    assert api.activate_window(object()) is False
    assert api.activate_window(None) is False


def test_noop_focused_window_center_returns_none() -> None:
    api = NoopWindowingApi()
    assert api.focused_window_center() is None
