from __future__ import annotations

from app.platform.models import SystemCommand


class MacOSSystemCommandProvider:
    def commands(self) -> list[SystemCommand]:
        return [
            SystemCommand(
                id="finder",
                name="Finder",
                icon="qta:mdi6.folder",
                description="打开 Finder",
                action="open -a Finder",
                keywords=["finder", "文件", "file", "文件管理器"],
            ),
            SystemCommand(
                id="system-settings",
                name="系统设置",
                icon="qta:mdi6.cog",
                description="打开系统设置",
                action='open -a "System Settings"',
                keywords=["设置", "settings", "system"],
            ),
            SystemCommand(
                id="terminal",
                name="终端",
                icon="qta:mdi6.console",
                description="打开终端",
                action="open -a Terminal",
                keywords=["terminal", "shell", "终端"],
            ),
            SystemCommand(
                id="activity-monitor",
                name="活动监视器",
                icon="qta:mdi6.chart-bar",
                description="打开活动监视器",
                action='open -a "Activity Monitor"',
                keywords=["activity", "monitor", "进程", "性能"],
            ),
            SystemCommand(
                id="calculator",
                name="计算器",
                icon="qta:mdi6.calculator",
                description="打开计算器",
                action="open -a Calculator",
                keywords=["calc", "计算", "math"],
            ),
            SystemCommand(
                id="restart-app",
                name="重启应用",
                icon="qta:mdi6.restart",
                description="快速重启桌面工具箱",
                action="__restart_app__",
                keywords=["restart", "reload", "重启", "刷新", "应用", "app"],
            ),
        ]
