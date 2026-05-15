from __future__ import annotations

from app.commands.command_index_db import CommandIndexDb
from app.logging import get_logger


class CommandUsageService:
    def __init__(self, index_db: CommandIndexDb) -> None:
        self._index_db = index_db
        self._log = get_logger("app.commands.usage_service")

    def usage_map(self) -> dict[str, tuple[int, str]]:
        try:
            return self._index_db.usage_map()
        except Exception as exc:
            self._log.warning("command.usage_read_failed", "读取命令使用记录失败", error=str(exc))
            return {}

    def record_plugin_launch(self, plugin_id: str) -> None:
        self._record_launch(f"plugin:{plugin_id}")

    def record_item_launch(self, item: dict) -> None:
        usage_key = item.get("usageKey")
        if usage_key:
            self._record_launch(str(usage_key))

    def _record_launch(self, usage_key: str) -> None:
        try:
            self._index_db.record_launch(usage_key)
        except Exception as exc:
            self._log.warning(
                "command.usage_record_failed",
                "记录命令使用次数失败",
                usageKey=usage_key,
                error=str(exc),
            )
