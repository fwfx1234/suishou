from __future__ import annotations

from app.platform.models import SystemCommand


class NoopSystemCommandProvider:
    def commands(self) -> list[SystemCommand]:
        return [
            SystemCommand(
                id="restart-app",
                name="重启应用",
                icon="qta:mdi6.restart",
                description="快速重启桌面工具箱",
                action="__restart_app__",
                keywords=["restart", "reload", "重启", "刷新", "应用", "app"],
            )
        ]
