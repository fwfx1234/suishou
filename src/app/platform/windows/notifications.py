from __future__ import annotations


class WindowsNotificationApi:
    """通过 QSystemTrayIcon.showMessage 兜底；Toast 后续做。"""

    def __init__(self) -> None:
        self._tray = None

    def set_tray(self, tray: object) -> None:
        self._tray = tray

    def notify(self, *, title: str, body: str, success: bool | None = None) -> bool:
        del success
        tray = self._tray
        if tray is None:
            return False
        show_message = getattr(tray, "showMessage", None)
        if not callable(show_message):
            return False
        try:
            show_message(title, body)
            return True
        except Exception:
            return False
