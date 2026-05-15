from __future__ import annotations

from app.plugins.manifest import PluginManifest
from app.plugins.runtime import PluginAction, PluginContext


def _log():
    from app.logging import get_logger

    return get_logger("features.app_launcher.runtime")


class AppLauncherListSession:
    """List-template session for launching system applications."""

    def __init__(self, manifest: PluginManifest, command_index: object, platform: object) -> None:
        self.manifest = manifest
        self.launch_mode = "list"
        self._command_index = command_index
        self._platform = platform
        self._query = ""
        self._ensure_apps()

    def create_qml_context(self) -> dict:
        return {}

    def qml_page(self) -> str:
        return ""

    def list_model(self) -> list[dict]:
        apps = self._command_index.search_apps(self._query, limit=50)
        return [self._to_list_item(app) for app in apps]

    def on_input_changed(self, text: str) -> list[dict]:
        self._query = text
        return self.list_model()

    def on_list_item_selected(self, item_id: str) -> None:
        app = self._find_app(item_id)
        if not app:
            return
        launch_path = str(app.get("launchPath") or "")
        if launch_path:
            self._command_index.record_launch_by_app_path(launch_path)
            result = self._platform.launch_application(app)
            if not result.ok:
                _log().warning("app.launch_failed", "应用启动失败", code=result.code, message=result.message, launchPath=launch_path)

    def on_list_item_action(self, item_id: str, action_id: str) -> list[dict]:
        del item_id
        if action_id == "rescan":
            self._rescan()
        return self.list_model()

    def close(self) -> None:
        return

    def _ensure_apps(self) -> None:
        if self._command_index.count_apps() == 0:
            self._rescan()

    def _rescan(self) -> None:
        apps = self._platform.scan_applications(extract_icons=False)
        self._command_index.sync_apps([app.to_db_dict() for app in apps])

    def _find_app(self, item_id: str) -> dict | None:
        for app in self._command_index.search_apps(self._query, limit=100):
            if str(app.get("id")) == item_id:
                return app
        return None

    @staticmethod
    def _to_list_item(app: dict) -> dict:
        icon_path = app.get("iconPath", "")
        icon = (
            "file:///" + str(icon_path).replace("\\", "/")
            if icon_path
            else "qta:mdi6.application-outline"
        )
        return {
            "id": str(app.get("id", "")),
            "title": str(app.get("name", "")),
            "subtitle": str(app.get("launchPath") or ""),
            "icon": icon,
            "payload": {"launchPath": app.get("launchPath") or ""},
        }


class AppLauncherRuntime:
    def on_enter(self, ctx: PluginContext, action: PluginAction) -> AppLauncherListSession:
        if ctx.command_index is None:
            raise RuntimeError("Command index is unavailable")
        platform = ctx.platform or ctx.services.platform
        if platform is None:
            raise RuntimeError("Platform API is unavailable")
        return AppLauncherListSession(action.manifest, ctx.command_index, platform)

    def on_exit(self) -> None:
        return


def create_runtime() -> AppLauncherRuntime:
    return AppLauncherRuntime()
