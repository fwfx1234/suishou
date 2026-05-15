from __future__ import annotations

from app.logging import get_logger
from app.commands.command_index_db import CommandIndexDb
from app.platform.services import PlatformServices


class CommandLauncher:
    def __init__(self, index_db: CommandIndexDb, platform_services: PlatformServices) -> None:
        self._index_db = index_db
        self._platform = platform_services
        self._log = get_logger("app.commands.command_launcher")

    def launch_external_item(self, item_id: str, source: str, payload: dict | None = None) -> str | None:
        payload = payload or {}
        if source == "system":
            action = str(payload.get("action") or "")
            if not action:
                return None
            self._record_launch(item_id if item_id.startswith("system:") else f"system:{item_id}")
            result = self._platform.external_launcher.launch_system_action(action)
            if result.ok:
                return str(payload.get("name") or item_id)
            self._log.warning("command.system_action_failed", "系统动作执行失败", action=action, code=result.code, message=result.message)
            return None

        if source == "app":
            launch_path = str(payload.get("launchPath") or "")
            if not launch_path:
                return None
            self._record_launch(f"app:{launch_path}")
            result = self._platform.external_launcher.launch_app(payload)
            if result.ok:
                return str(payload.get("name") or launch_path)
            self._log.warning("command.app_launch_failed", "应用启动失败", launchPath=launch_path, code=result.code, message=result.message)
            return None

        return None

    def _record_launch(self, usage_key: str) -> None:
        try:
            self._index_db.record_launch(usage_key)
        except Exception as exc:
            self._log.warning("command.launch_usage_record_failed", "记录启动使用次数失败", usageKey=usage_key, error=str(exc))
