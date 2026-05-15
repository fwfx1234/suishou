from __future__ import annotations

from collections.abc import Callable
from threading import Lock, Thread

from app.logging import get_logger
from app.commands.command_index_db import CommandIndexDb
from app.platform.services import PlatformServices


class AppIndexService:
    def __init__(self, index_db: CommandIndexDb, platform_services: PlatformServices) -> None:
        self._index_db = index_db
        self._platform = platform_services
        self._apps_scanned = False
        self._app_scan_running = False
        self._app_scan_lock = Lock()
        self._index_lock = Lock()
        self._callbacks: list[Callable[[], None]] = []
        self._log = get_logger("app.commands.app_index_service")

    @property
    def index_lock(self) -> Lock:
        return self._index_lock

    @property
    def scan_running(self) -> bool:
        with self._app_scan_lock:
            return self._app_scan_running

    def on_scan_completed(self, callback: Callable[[], None]) -> None:
        self._callbacks.append(callback)

    def ensure_scan_started(self) -> None:
        if self.scan_running:
            return
        with self._index_lock:
            needs_scan = not self._apps_scanned and self._index_db.count_apps() == 0
        if needs_scan:
            self.start_scan()

    def start_scan(self, *, force: bool = False) -> bool:
        with self._app_scan_lock:
            if self._app_scan_running:
                return False
            if self._apps_scanned and not force:
                return False
            self._app_scan_running = True

        def run_scan() -> None:
            try:
                apps = self._platform.app_indexer.scan_apps(extract_icons=False)
                with self._index_lock:
                    self._index_db.sync_apps([app.to_db_dict() for app in apps])
                self._apps_scanned = True
                self._log.info("command.app_scan.complete", "应用索引扫描完成", count=len(apps))
            except Exception as exc:
                self._log.warning("command.app_scan_failed", "应用索引扫描失败", error=str(exc))
            finally:
                with self._app_scan_lock:
                    self._app_scan_running = False
                for callback in list(self._callbacks):
                    try:
                        callback()
                    except Exception as exc:
                        self._log.warning("command.app_scan_callback_failed", "应用索引扫描回调失败", error=str(exc))

        Thread(target=run_scan, name="app-index-scan", daemon=True).start()
        return True
