from __future__ import annotations


class NoopWindowingApi:
    def configure_launcher_window(self, window: object) -> bool:
        return False

    def configure_overlay_window(self, window: object, *, force_top: bool = True) -> bool:
        return False

    def activate_window(self, window: object | None = None) -> bool:
        return False

    def focused_window_center(self) -> tuple[int, int] | None:
        return None
