"""系统托盘管理：托盘图标 + 右键菜单。"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QSystemTrayIcon, QMenu


class SystemTrayManager(QObject):
    """管理系统托盘图标和菜单。"""

    showWindowRequested = Signal()
    restartRequested = Signal()
    quitRequested = Signal()

    def __init__(self, platform_services: object, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._platform_services = platform_services
        self._tray = QSystemTrayIcon(parent)
        self._build_icon()
        self._tray.setToolTip("桌面工具箱")

        menu = QMenu()
        show_action = menu.addAction("显示/隐藏")
        show_action.triggered.connect(self.showWindowRequested.emit)
        restart_action = menu.addAction("重启应用")
        restart_action.triggered.connect(self.restartRequested.emit)
        menu.addSeparator()
        quit_action = menu.addAction("退出")
        quit_action.triggered.connect(self.quitRequested.emit)
        self._tray.setContextMenu(menu)

        # 双击托盘图标显示窗口
        self._tray.activated.connect(self._on_activated)

        # Windows 通知通道依赖托盘做兜底显示，构造完成后回填托盘引用。
        notifications = getattr(platform_services, "notifications", None)
        set_tray = getattr(notifications, "set_tray", None)
        if callable(set_tray):
            set_tray(self._tray)

    def _build_icon(self) -> None:
        try:
            import qtawesome as qta

            packaged = self._platform_services.paths.is_frozen()
            appearance = self._platform_services.tray_appearance
            color = appearance.icon_color(packaged=packaged)
            icon = qta.icon("fa5s.rocket", color=color)
            appearance.apply_mask(icon, packaged=packaged)
            self._tray.setIcon(icon)
        except Exception:
            self._tray.setIcon(QIcon())

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showWindowRequested.emit()

    def show(self) -> None:
        self._tray.show()

    def hide(self) -> None:
        self._tray.hide()

    def show_message(self, title: str, message: str) -> None:
        self._platform_services.notifications.notify(title=title, body=message)
