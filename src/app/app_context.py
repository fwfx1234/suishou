from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from random import randint
from time import perf_counter
from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from app.app_view_model import AppViewModel
from app.commands.command_index_db import CommandIndexDb
from app.commands.command_service import CommandService
from app.commands.dynamic_command_registry import DynamicCommandRegistry
from app.diagnostics import MemoryProbe, install_periodic_snapshot, snapshot
from app.launcher.launcher_bridge import LauncherBridge
from app.launcher_runtime_coordinator import LauncherRuntimeCoordinator
from app.platform.services import PlatformServices
from app.plugin_surface_coordinator import PluginSurfaceCoordinator
from app.plugins.background_manager import BackgroundManager
from app.plugins.manifest import PluginManifest
from app.plugins.plugin_manager import PluginManager
from app.plugins.runtime import PluginContext
from app.plugins.session_manager import PluginSessionManager
from app.settings import configured_bool, configured_int
from app.storage import StorageManager
from app.tray_coordinator import TrayCoordinator


@dataclass(slots=True, weakref_slot=True)
class ApplicationContext:
    qt_app: QApplication
    log: Any
    app_dir: Path
    main_qml: Path
    plugin_window_qml: Path
    engine: QQmlApplicationEngine
    app_vm: AppViewModel
    platform_services: PlatformServices
    storage: StorageManager
    dynamic_commands: DynamicCommandRegistry
    command_index: CommandIndexDb
    manifests: list[PluginManifest]
    plugin_manager: PluginManager
    plugin_context: PluginContext
    background_manager: BackgroundManager
    command_service: CommandService
    launcher_bridge: LauncherBridge
    session_manager: PluginSessionManager
    surface_coordinator: PluginSurfaceCoordinator
    runtime_coordinator: LauncherRuntimeCoordinator
    tray_coordinator: TrayCoordinator
    launcher_window: object | None = None
    _shutting_down: bool = field(default=False, init=False)
    _app_index_refresh_timer: QTimer | None = field(default=None, init=False)
    _memory_probe_timer: QTimer | None = field(default=None, init=False)

    def start(self) -> None:
        started_at = perf_counter()
        connect_started_at = perf_counter()
        self.runtime_coordinator.connect()
        self.log.debug("app.context.signals_connected", "运行信号连接完成", elapsedMs=int((perf_counter() - connect_started_at) * 1000))
        hotkeys_started_at = perf_counter()
        self.runtime_coordinator.install_hotkeys()
        self.log.debug("app.context.hotkeys_install_scheduled", "热键安装已调度", elapsedMs=int((perf_counter() - hotkeys_started_at) * 1000))
        self.qt_app.aboutToQuit.connect(self.shutdown)
        tray_started_at = perf_counter()
        self.tray_coordinator.show()
        self.log.debug("app.context.tray_show_complete", "系统托盘显示完成", elapsedMs=int((perf_counter() - tray_started_at) * 1000))
        QTimer.singleShot(100, self.runtime_coordinator.start_background_plugins)
        QTimer.singleShot(250, self._start_initial_app_index_scan)
        self._schedule_app_index_refresh()
        self._install_memory_probe()
        self.log.debug("app.context.start_scheduled", "后台插件启动已调度", elapsedMs=int((perf_counter() - started_at) * 1000))

    def shutdown(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        try:
            self.log.debug("app.memory.shutdown", "应用退出前内存快照", **snapshot(
                sessions_count=len(getattr(self.session_manager, "_sessions", {}) or {}),
                windows_count=len(getattr(self.surface_coordinator, "_windows", {}) or {}),
            ))
        except Exception:
            pass
        if self._memory_probe_timer is not None:
            self._memory_probe_timer.stop()
            self._memory_probe_timer.deleteLater()
            self._memory_probe_timer = None
        if self._app_index_refresh_timer is not None:
            self._app_index_refresh_timer.stop()
            self._app_index_refresh_timer.deleteLater()
            self._app_index_refresh_timer = None
        self.runtime_coordinator.shutdown()
        self.surface_coordinator.destroy_all()
        self.session_manager.close_all()
        self.background_manager.stop_all()
        self.plugin_manager.close_all()
        self.command_service.shutdown()
        self.command_index.close()

    def _install_memory_probe(self) -> None:
        interval_ms = configured_int(
            "diagnostics.memorySnapshotMs", ("SUISHOU_MEM_SNAPSHOT_MS", "PY_DESKTOP_MEM_SNAPSHOT_MS"), 0
        )
        if interval_ms <= 0:
            return
        include_qobject_top = bool(
            configured_bool(
                "diagnostics.memoryQObjectStats", ("SUISHOU_MEM_QOBJECT_STATS", "PY_DESKTOP_MEM_QOBJECT_STATS"), False
            )
        )
        probe = MemoryProbe(
            session_manager=self.session_manager,
            surface_coordinator=self.surface_coordinator,
            include_qobject_top=include_qobject_top,
        )
        self._memory_probe_timer = install_periodic_snapshot(
            self.qt_app, probe, interval_ms, log=self.log.debug
        )
        self.log.debug(
            "app.memory.probe_installed",
            "内存探针已安装",
            intervalMs=interval_ms,
            includeQObjectTop=include_qobject_top,
        )

    def _start_initial_app_index_scan(self) -> None:
        started = self.command_service.check_app_index_changes(force=True)
        self.log.debug("app.index.initial_check", "应用索引初始检查已调度", started=started)

    def _schedule_app_index_refresh(self) -> None:
        if self._shutting_down:
            return
        if self._app_index_refresh_timer is None:
            self._app_index_refresh_timer = QTimer()
            self._app_index_refresh_timer.setSingleShot(True)
            self._app_index_refresh_timer.timeout.connect(self._refresh_app_index_in_background)
        interval_ms = randint(20 * 60_000, 45 * 60_000)
        self._app_index_refresh_timer.start(interval_ms)
        self.log.debug("app.index.refresh_scheduled", "后台应用索引刷新已调度", intervalMs=interval_ms)

    def _refresh_app_index_in_background(self) -> None:
        if self._shutting_down:
            return
        started = self.command_service.check_app_index_changes(force=True)
        self.log.debug("app.index.background_check", "后台应用索引检查已触发", started=started)
        self._schedule_app_index_refresh()
