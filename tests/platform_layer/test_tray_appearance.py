from __future__ import annotations

from app.platform.macos.tray_appearance import MacOSTrayAppearance
from app.platform.noop.tray_appearance import NoopTrayAppearance
from app.platform.windows.tray_appearance import WindowsTrayAppearance


def test_icon_color_packaged_is_white() -> None:
    for cls in (MacOSTrayAppearance, WindowsTrayAppearance, NoopTrayAppearance):
        assert cls().icon_color(packaged=True) == "#FFFFFF"


def test_icon_color_dev_is_purple() -> None:
    for cls in (MacOSTrayAppearance, WindowsTrayAppearance, NoopTrayAppearance):
        assert cls().icon_color(packaged=False) == "#8B5CF6"


def test_macos_apply_mask_when_packaged_calls_set_is_mask() -> None:
    calls: list[bool] = []

    class FakeIcon:
        def setIsMask(self, value: bool) -> None:
            calls.append(value)

    MacOSTrayAppearance().apply_mask(FakeIcon(), packaged=True)
    assert calls == [True]


def test_macos_apply_mask_dev_is_noop() -> None:
    calls: list[bool] = []

    class FakeIcon:
        def setIsMask(self, value: bool) -> None:
            calls.append(value)

    MacOSTrayAppearance().apply_mask(FakeIcon(), packaged=False)
    assert calls == []


def test_macos_apply_mask_without_setter_is_silent() -> None:
    MacOSTrayAppearance().apply_mask(object(), packaged=True)  # no AttributeError


def test_windows_apply_mask_is_noop() -> None:
    calls: list[bool] = []

    class FakeIcon:
        def setIsMask(self, value: bool) -> None:
            calls.append(value)

    WindowsTrayAppearance().apply_mask(FakeIcon(), packaged=True)
    assert calls == []
