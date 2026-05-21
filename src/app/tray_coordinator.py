from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject

from .tray.system_tray_manager import SystemTrayManager


class TrayCoordinator:
    def __init__(
        self,
        *,
        parent: QObject,
        platform_services: object,
        on_show_window: Callable[[], None],
        on_restart: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self._manager = SystemTrayManager(platform_services=platform_services, parent=parent)
        self._manager.showWindowRequested.connect(on_show_window)
        self._manager.restartRequested.connect(on_restart)
        self._manager.quitRequested.connect(on_quit)

    def show(self) -> None:
        self._manager.show()

    def hide(self) -> None:
        self._manager.hide()

    def show_message(self, title: str, message: str) -> None:
        self._manager.show_message(title, message)
