from __future__ import annotations

import subprocess


class MacOSNotificationApi:
    def notify(self, *, title: str, body: str, success: bool | None = None) -> bool:
        safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
        safe_body = body.replace("\\", "\\\\").replace('"', '\\"')
        if success is None:
            script = f'display notification "{safe_body}" with title "{safe_title}"'
        else:
            subtitle = "成功" if success else "失败"
            script = (
                f'display notification "{safe_body}" with title "{safe_title}" '
                f'subtitle "{subtitle}"'
            )
        try:
            subprocess.Popen(
                ["osascript", "-e", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except OSError:
            return False
