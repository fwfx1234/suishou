from __future__ import annotations

from app.logging import get_logger


class NoopNotificationApi:
    def __init__(self) -> None:
        self._log = get_logger("app.platform.noop.notifications")

    def notify(self, *, title: str, body: str, success: bool | None = None) -> bool:
        self._log.debug("notification.suppressed", "通知未发送", title=title, body=body, success=success)
        return False
