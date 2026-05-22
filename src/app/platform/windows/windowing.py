from __future__ import annotations


class WindowsWindowingApi:
    """Windows 桌面窗口管理。

    第一版以 Qt 的 `WindowStaysOnTopHint | Tool` flag 为主体（QML 端已设置），
    本类仅提供"提升到前台"兜底；窗口装饰仍由 Qt 处理。
    """

    def configure_launcher_window(self, window: object) -> bool:
        return self._set_topmost(window)

    def configure_overlay_window(self, window: object, *, force_top: bool = True) -> bool:
        if not force_top:
            return False
        return self._set_topmost(window)

    def activate_window(self, window: object | None = None) -> bool:
        try:
            import win32gui  # type: ignore

            try:
                import win32con  # type: ignore

                win32gui.AllowSetForegroundWindow(getattr(win32con, "ASFW_ANY", -1))
            except Exception:
                pass
            hwnd = self._hwnd(window) if window is not None else win32gui.GetForegroundWindow()
            if not hwnd:
                return False
            win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception:
            return False

    def activate_launcher_window(self, window: object) -> bool:
        return self.activate_window(window)

    def activate_overlay_window(self, window: object) -> bool:
        return self.activate_window(window)

    def should_request_qt_activation(self) -> bool:
        return True

    def focused_window_center(self) -> tuple[int, int] | None:
        try:
            import win32gui  # type: ignore

            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            if width <= 1 or height <= 1:
                return None
            return left + width // 2, top + height // 2
        except Exception:
            return None

    @staticmethod
    def _hwnd(window: object | None) -> int:
        if window is None:
            return 0
        try:
            value = int(window.winId())
        except Exception:
            return 0
        return value

    def _set_topmost(self, window: object) -> bool:
        hwnd = self._hwnd(window)
        if not hwnd:
            return False
        try:
            import win32gui  # type: ignore
            import win32con  # type: ignore

            flags = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, flags)
            return True
        except Exception:
            return False
