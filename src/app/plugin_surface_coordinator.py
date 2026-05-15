"""Manages QML plugin windows and inline/list host surfaces."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import shiboken6
from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtGui import QIcon, QCursor
from PySide6.QtQml import QQmlComponent, QQmlApplicationEngine

from app.logging import get_logger
from app.plugins.runtime import PluginSession
from app.plugins.session_manager import SessionState


@dataclass(slots=True)
class PluginWindowSurface:
    """Track the live QML window that hosts a plugin session."""

    plugin_id: str
    window: QObject
    hidden_for_retention: bool = False


def _icon_from_manifest(value: str, app_dir: Path) -> QIcon:
    if not value:
        return QIcon()
    if value.startswith("qta:"):
        try:
            import qtawesome as qta
            return qta.icon(value.removeprefix("qta:"), color="#8B5CF6")
        except Exception:
            return QIcon()
    if value.startswith("file:///"):
        return QIcon(QUrl(value).toLocalFile())
    if value.startswith("qrc:/") or value.startswith(":/"):
        return QIcon(value)
    icon_path = app_dir / "assets" / "icons" / f"{value}.svg"
    if icon_path.exists():
        return QIcon(str(icon_path))
    return QIcon(value)


def _plugin_window_config(session: PluginSession, screen: object = None) -> dict:
    options = session.manifest.window_options or {}
    if options.get("fullscreen"):
        return {"fullscreen": True, "width": 800, "height": 600}
    if screen is not None:
        screen_geo = screen.availableGeometry()
        sw, sh = screen_geo.width(), screen_geo.height()
    else:
        sw, sh = 1920, 1080
    return {
        "fullscreen": False,
        "width": _resolve_dimension(options.get("width"), sw, 800),
        "height": _resolve_dimension(options.get("height"), sh, 600),
    }


def _resolve_dimension(value: object, screen_size: int, default: int) -> int:
    if value is None:
        return default
    try:
        num = float(value)
    except (TypeError, ValueError):
        return default
    if num < 1.0:
        return max(400, int(screen_size * num))
    return max(400, int(num))


def _is_qobject_alive(obj: object) -> bool:
    if obj is None:
        return False
    try:
        return shiboken6.isValid(obj)
    except RuntimeError:
        return False


def is_qobject_alive(obj: object) -> bool:
    return _is_qobject_alive(obj)


def _set_window_size_if_alive(win: object, width: int, height: int) -> None:
    if not _is_qobject_alive(win):
        return
    try:
        win.setWidth(width)
        win.setHeight(height)
    except RuntimeError as exc:
        if "already deleted" in str(exc) or "Internal C++ object" in str(exc):
            return
        raise


def _center_window_once(win: object, screen: object, width: int, height: int) -> None:
    if screen is None or not _is_qobject_alive(win):
        return
    geometry = screen.availableGeometry()
    x = geometry.x() + max(0, (geometry.width() - width) // 2)
    y = geometry.y() + max(0, (geometry.height() - height) // 2)
    win.setX(x)
    win.setY(y)


class PluginSurfaceCoordinator:
    """Creates and manages QML surfaces for plugin sessions.

    Handles independent windows, inline host integration, list mode,
    window retention/hide on close, and full destruction when sessions expire.
    """

    def __init__(
        self,
        engine: QQmlApplicationEngine,
        qt_app: object,
        *,
        plugin_window_qml_path: str,
        app_dir: Path,
        launcher_bridge: object | None = None,
        launcher_window: object | None = None,
        on_retained_close: Callable[[str, str], None] | None = None,
    ) -> None:
        self._engine = engine
        self._qt_app = qt_app
        self._plugin_window_qml_path = plugin_window_qml_path
        self._app_dir = app_dir
        self._bridge = launcher_bridge
        self._launcher_window = launcher_window
        self._on_retained_close = on_retained_close
        self._windows: dict[str, PluginWindowSurface] = {}
        self._log = get_logger("app.plugin_surface_coordinator")

    def show(
        self,
        plugin_id: str,
        session: PluginSession,
        *,
        input_text: str = "",
        payload: dict | None = None,
    ) -> bool:
        launch_mode = session.launch_mode
        if payload and payload.get("openInWindow"):
            launch_mode = "window"

        if launch_mode == "none":
            if self._launcher_window is not None and _is_qobject_alive(self._launcher_window):
                self._launcher_window.hide()
            return True
        if launch_mode == "list":
            if self._bridge is not None:
                self._bridge.setPluginListItems(session.list_model())
            self._show_list_plugin(plugin_id, input_text, payload or {})
            return True
        if launch_mode == "inline_view":
            self._show_inline_plugin(plugin_id, session, input_text, payload or {})
            return True
        return self._show_window_surface(plugin_id, session)

    def suspend(self, plugin_id: str, host: str) -> None:
        if host == "window":
            return
        if host == "list":
            if self._bridge is not None:
                self._bridge.setPluginListItems([])
            return
        if self._bridge is not None:
            self._bridge.setPluginListItems([])
        self._notify_inline_host_retained(plugin_id)

    def destroy(self, plugin_id: str) -> None:
        surface = self._windows.pop(plugin_id, None)
        if surface is None:
            return
        win = surface.window
        if not _is_qobject_alive(win):
            return
        try:
            win.setProperty("retainOnClose", False)
            win.close()
        except RuntimeError:
            return

    def destroy_all(self) -> None:
        for surface in list(self._windows.values()):
            if _is_qobject_alive(surface.window):
                try:
                    surface.window.setProperty("retainOnClose", False)
                    surface.window.close()
                except RuntimeError:
                    pass

    def notify_retention_expired(self, plugin_id: str, state: SessionState) -> None:
        host = self._host_from_state(state)
        if host == "window":
            self.destroy(plugin_id)
        else:
            if self._bridge is not None:
                self._bridge.retainedPluginExpired.emit(plugin_id)

    def _show_window_surface(self, plugin_id: str, session: PluginSession) -> bool:
        surface = self._get_live_surface(plugin_id)
        if surface is not None:
            try:
                surface.hidden_for_retention = False
                surface.window.show()
                surface.window.raise_()
                surface.window.requestActivate()
                return True
            except RuntimeError:
                self._windows.pop(plugin_id, None)
        return self._open_independent_window(plugin_id, session)

    def _open_independent_window(self, plugin_id: str, session: PluginSession) -> bool:
        manifest = session.manifest
        target_screen = None
        if self._launcher_window is not None:
            try:
                target_screen = self._launcher_window.screen()
            except RuntimeError:
                target_screen = None
        if target_screen is None:
            target_screen = self._qt_app.screenAt(QCursor.pos()) or self._qt_app.primaryScreen()

        wc = _plugin_window_config(session, target_screen)
        component = QQmlComponent(self._engine, QUrl.fromLocalFile(self._plugin_window_qml_path))
        win = component.createWithInitialProperties(
            {
                "pluginId": plugin_id,
                "pluginName": manifest.name,
                "qmlPage": session.qml_page(),
                "initialWidth": wc["width"],
                "initialHeight": wc["height"],
                "retainOnClose": True,
            }
        )
        if win is None:
            self._log.error("plugin.window.create_failed", "创建插件窗口失败", pluginId=plugin_id, error=component.errorString())
            return False

        win.setProperty("pluginId", plugin_id)
        win.setProperty("pluginName", manifest.name)
        win.setProperty("qmlPage", session.qml_page())
        win.setProperty("initialWidth", wc["width"])
        win.setProperty("initialHeight", wc["height"])
        win.setProperty("retainOnClose", True)
        if wc["fullscreen"]:
            win.showFullScreen()
        else:
            win.setWidth(wc["width"])
            win.setHeight(wc["height"])
        if hasattr(win, "setIcon"):
            win.setIcon(_icon_from_manifest(manifest.icon, self._app_dir))

        if not wc["fullscreen"]:
            _center_window_once(win, target_screen, wc["width"], wc["height"])

        def _on_retained_close(pid: str) -> None:
            surface = self._windows.get(pid)
            if surface is not None:
                surface.hidden_for_retention = True
            if self._on_retained_close is not None:
                self._on_retained_close(pid, "window")

        win.retainedCloseRequested.connect(_on_retained_close)
        win.destroyed.connect(lambda _obj=None, pid=plugin_id: self._windows.pop(pid, None))

        self._windows[plugin_id] = PluginWindowSurface(plugin_id=plugin_id, window=win)

        if self._launcher_window is not None:
            self._launcher_window.hide()

        win.show()
        if not wc["fullscreen"]:
            QTimer.singleShot(
                0,
                lambda w=win, width=wc["width"], height=wc["height"]: _set_window_size_if_alive(
                    w, width, height
                ),
            )
        win.requestActivate()
        return True

    def _show_inline_plugin(self, plugin_id: str, session: PluginSession, input_text: str, payload: dict) -> None:
        if self._launcher_window is None or not _is_qobject_alive(self._launcher_window):
            return
        self._launcher_window.enterPluginMode(
            plugin_id,
            "inline_view",
            input_text,
            bool(payload.get("clearLauncherInputOnEnter")),
            session.qml_page(),
        )

    def _show_list_plugin(self, plugin_id: str, input_text: str, payload: dict) -> None:
        if self._launcher_window is None or not _is_qobject_alive(self._launcher_window):
            return
        self._launcher_window.enterPluginMode(
            plugin_id,
            "list",
            input_text,
            bool(payload.get("clearLauncherInputOnEnter")),
            "",
        )

    def _get_live_surface(self, plugin_id: str) -> PluginWindowSurface | None:
        surface = self._windows.get(plugin_id)
        if surface is None:
            return None
        if not _is_qobject_alive(surface.window):
            self._windows.pop(plugin_id, None)
            return None
        return surface

    def _notify_inline_host_retained(self, plugin_id: str) -> None:
        if self._launcher_window is not None and _is_qobject_alive(self._launcher_window):
            self._launcher_window.retainInlineHost(plugin_id)

    @staticmethod
    def _host_from_state(state: SessionState) -> str:
        return state.host
