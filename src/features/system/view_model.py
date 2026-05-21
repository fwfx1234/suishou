from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from weakref import ref

from PySide6.QtCore import QObject, Property, Signal, Slot

from app.paths import data_dir, plugin_dirs
from app.plugins.manifest_loader import load_all_plugin_manifests
from app.services.clipboard.models import DEFAULT_CLIPBOARD_CONFIG
from app.settings import configured_bool, configured_int, configured_text, get_app_settings_store, parse_bool, setting_source


@dataclass(frozen=True, slots=True)
class SettingSpec:
    key: str
    label: str
    kind: str
    default: object
    env: str = ""
    restart_required: bool = True
    description: str = ""
    options: tuple[str, ...] = ()
    minimum: int | None = None
    maximum: int | None = None


SETTING_SPECS = [
    SettingSpec("paths.dataDir", "数据目录", "path", "", "PY_DESKTOP_TOOLS_DATA_DIR", True, "存放数据库、缓存和设置文件。"),
    SettingSpec("logging.logDir", "日志路径", "path", "", "PY_DESKTOP_TOOLS_LOG_DIR", True, "app.log、error.log、qt.log 与插件日志目录。"),
    SettingSpec("paths.pluginDirs", "外部插件目录", "pathList", "", "PY_DESKTOP_TOOLS_PLUGIN_DIR", True, "多个目录使用系统路径分隔符连接。"),
    SettingSpec("developer.qmlHotReload", "QML 热重载", "bool", False, "PY_DESKTOP_QML_HOT_RELOAD", True, "开发时监听 QML 文件变更并重载。"),
    SettingSpec("logging.console", "控制台日志", "bool", None, "PY_DESKTOP_TOOLS_LOG_CONSOLE", True, "是否同时输出日志到终端。"),
    SettingSpec("logging.consoleLevel", "控制台日志等级", "choice", "WARNING", "PY_DESKTOP_TOOLS_LOG_LEVEL", True, "控制终端日志输出阈值。", ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")),
    SettingSpec("logging.fileLevel", "文件日志等级", "choice", "WARNING", "PY_DESKTOP_TOOLS_LOG_FILE_LEVEL", True, "控制 app.log 和插件日志输出阈值。", ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")),
    SettingSpec("logging.qtLevel", "Qt 日志等级", "choice", "WARNING", "PY_DESKTOP_TOOLS_QT_LOG_LEVEL", True, "控制 qt.log 输出阈值。", ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")),
    SettingSpec("logging.retentionDays", "日志保留天数", "int", 7, "PY_DESKTOP_TOOLS_LOG_RETENTION_DAYS", True, "日志滚动文件保留天数。", minimum=1, maximum=365),
    SettingSpec("plugins.retentionMs", "插件会话保留毫秒", "int", 300000, "PY_DESKTOP_PLUGIN_RETENTION_MS", True, "插件窗口关闭后的状态保留时间。", minimum=1000, maximum=86400000),
    SettingSpec("hotkeys.launcher", "启动器热键", "text", "Alt+Space", "", True, "全局唤起启动器的快捷键。"),
    SettingSpec("clipboard.captureText", "剪贴板记录文本", "bool", True, "", False, "是否把文本内容写入剪贴板历史。"),
    SettingSpec("clipboard.captureImage", "剪贴板记录图片", "bool", True, "", False, "是否把图片内容写入剪贴板历史。"),
    SettingSpec("clipboard.captureFiles", "剪贴板记录文件", "bool", True, "", False, "是否把文件路径写入剪贴板历史。"),
    SettingSpec("clipboard.maxTextChars", "剪贴板文本上限", "int", 20000, "", False, "超过该字符数的文本不会进入历史。", minimum=100, maximum=2000000),
    SettingSpec("clipboard.hotkey", "剪贴板热键", "text", "Alt+V", "", False, "打开剪贴板历史窗口的快捷键。"),
    SettingSpec("hotkeys.windowsFallbackHook", "Windows 低级键盘 Hook", "choice", "", "PY_DESKTOP_TOOLS_HOTKEY_HOOK", True, "控制 Windows 原生热键失败时是否启用低级键盘 Hook。", ("", "always", "never")),
]

_SPECS_BY_KEY = {item.key: item for item in SETTING_SPECS}
_CLIPBOARD_KEYS = {
    "clipboard.captureText": "capture_text",
    "clipboard.captureImage": "capture_image",
    "clipboard.captureFiles": "capture_files",
    "clipboard.maxTextChars": "max_text_chars",
    "clipboard.hotkey": "hotkey",
}


def _clipboard_config_key(key: str) -> str:
    return _CLIPBOARD_KEYS.get(key, key)


class SystemSettingsViewModel(QObject):
    appIndexChanged = Signal()
    permissionsChanged = Signal()
    settingsChanged = Signal()

    def __init__(
        self,
        command_service: object | None = None,
        permissions: object | None = None,
        storage: object | None = None,
        platform: object | None = None,
        clipboard: object | None = None,
    ) -> None:
        super().__init__()
        self._command_service = command_service
        self._permissions = permissions
        self._storage = storage
        self._platform = platform
        self._clipboard = clipboard
        self._settings = get_app_settings_store()
        self._runtime_values = self._capture_runtime_values()
        self._disposed = False
        if command_service is not None:
            on_completed = getattr(command_service, "on_app_scan_completed", None)
            if callable(on_completed):
                self_ref = ref(self)

                def notify() -> None:
                    obj = self_ref()
                    if obj is not None and not obj._disposed:
                        obj.appIndexChanged.emit()

                on_completed(notify)

    @Property(bool, notify=appIndexChanged)
    def appScanRunning(self) -> bool:
        if self._command_service is None:
            return False
        return bool(getattr(self._command_service, "app_scan_running", False))

    @Property(int, notify=appIndexChanged)
    def appCount(self) -> int:
        if self._command_service is None:
            return 0
        count_apps = getattr(self._command_service, "count_apps", None)
        if not callable(count_apps):
            return 0
        try:
            return int(count_apps())
        except Exception:
            return 0

    @Property(str, constant=True)
    def pathSeparator(self) -> str:
        return os.pathsep

    @Property("QVariantList", notify=settingsChanged)
    def settingsItems(self) -> list[dict]:
        return [self._item_for_spec(spec) for spec in SETTING_SPECS]

    @Property(bool, notify=settingsChanged)
    def restartRequired(self) -> bool:
        return any(self._item_for_spec(spec)["pending"] for spec in SETTING_SPECS if spec.restart_required)

    @Slot(result="QVariantMap")
    def diagnostics(self) -> dict:
        manifests = load_all_plugin_manifests()
        background = [item.id for item in manifests if item.activation == "background"]
        root = Path(str(self._effective_value(_SPECS_BY_KEY["paths.dataDir"]))).expanduser()
        configured_log_dir = self._effective_value(_SPECS_BY_KEY["logging.logDir"])
        log_dir = Path(str(configured_log_dir)).expanduser() if str(configured_log_dir or "").strip() else root / "logs"
        return {
            "dataDir": str(root),
            "logDir": str(log_dir),
            "settingsFile": str(self._settings.path),
            "pluginDirs": os.pathsep.join(str(path) for path in plugin_dirs()),
            "pluginCount": len(manifests),
            "backgroundPlugins": ", ".join(background) if background else "无",
            "platform": getattr(getattr(self._platform, "info", None), "display_name", "") or sys.platform,
        }

    @Slot(str, result="QVariantMap")
    def settingItem(self, key: str) -> dict:
        spec = _SPECS_BY_KEY.get(str(key))
        return self._item_for_spec(spec) if spec is not None else {}

    @Slot(str, object, result=bool)
    def setSetting(self, key: str, value) -> bool:
        spec = _SPECS_BY_KEY.get(str(key))
        if spec is None:
            return False
        normalized = self._normalize_value(spec, value)
        if spec.key.startswith("clipboard."):
            self._set_clipboard_config(spec.key, normalized)
        else:
            self._settings.set(spec.key, normalized)
        self.settingsChanged.emit()
        return True

    @Slot(str, result=bool)
    def resetSetting(self, key: str) -> bool:
        spec = _SPECS_BY_KEY.get(str(key))
        if spec is None:
            return False
        if spec.key.startswith("clipboard."):
            self._set_clipboard_config(spec.key, self._resolved_default(spec))
        else:
            self._settings.delete(spec.key)
        self.settingsChanged.emit()
        return True

    @Slot(result=bool)
    def restartApp(self) -> bool:
        return False

    @Slot(str, result=bool)
    def openPath(self, path: str) -> bool:
        if self._platform is None:
            return False
        open_path = getattr(self._platform, "open_path", None)
        if not callable(open_path):
            return False
        try:
            result = open_path(Path(str(path)).expanduser())
        except Exception:
            return False
        return bool(getattr(result, "ok", False))

    @Property(str, notify=permissionsChanged)
    def accessibilityStatusText(self) -> str:
        status = self._accessibility_status()
        code = str(status.get("status") or "unknown")
        if code == "authorized":
            return "辅助功能权限：已授权"
        if code == "not_authorized":
            return "辅助功能权限：未授权"
        if code == "not_required":
            return "辅助功能权限：无需授权"
        return "辅助功能权限：未知"

    @Property(bool, notify=permissionsChanged)
    def accessibilityAuthorized(self) -> bool:
        return str(self._accessibility_status().get("status") or "") in {"authorized", "not_required"}

    @Slot()
    def refreshPermissions(self) -> None:
        self.permissionsChanged.emit()

    @Slot(result=bool)
    def openAccessibilitySettings(self) -> bool:
        if self._permissions is None:
            return False
        open_settings = getattr(self._permissions, "open_accessibility_settings", None)
        if not callable(open_settings):
            return False
        try:
            result = open_settings()
        except Exception:
            return False
        self.permissionsChanged.emit()
        return bool(getattr(result, "ok", False))

    @Slot(result=bool)
    def rescanApplications(self) -> bool:
        if self._command_service is None:
            return False
        start = getattr(self._command_service, "start_app_scan", None)
        if not callable(start):
            return False
        started = bool(start(force=True))
        self.appIndexChanged.emit()
        return started

    def dispose(self) -> None:
        self._disposed = True

    def _item_for_spec(self, spec: SettingSpec) -> dict:
        saved = self._stored_value(spec)
        effective = self._effective_value(spec)
        default = self._resolved_default(spec)
        source = self._source_for_spec(spec)
        display_value = effective if source == "env" else (saved if saved is not None else default)
        return {
            "key": spec.key,
            "label": spec.label,
            "kind": spec.kind,
            "value": display_value,
            "effectiveValue": effective,
            "defaultValue": default,
            "env": spec.env,
            "source": source,
            "sourceText": self._source_text(source),
            "restartRequired": spec.restart_required,
            "pending": source == "settings" and saved != effective,
            "description": spec.description,
            "options": list(spec.options),
            "minimum": spec.minimum if spec.minimum is not None else 0,
            "maximum": spec.maximum if spec.maximum is not None else 0,
        }

    def _effective_value(self, spec: SettingSpec):
        if spec.key.startswith("clipboard."):
            return self._clipboard_config_value(spec.key)
        return self._runtime_values.get(spec.key, self._resolved_default(spec))

    def _resolved_default(self, spec: SettingSpec):
        if spec.key == "paths.dataDir":
            return self._default_data_dir()
        if spec.key == "logging.logDir":
            return str(Path(self._default_data_dir()) / "logs")
        if spec.key == "paths.pluginDirs":
            return str(Path(__file__).resolve().parents[3] / "plugins")
        if spec.key == "logging.console" and spec.default is None:
            return not bool(getattr(sys, "frozen", False))
        if spec.key.startswith("clipboard."):
            return DEFAULT_CLIPBOARD_CONFIG.get(_clipboard_config_key(spec.key), spec.default)
        return spec.default

    def _capture_runtime_values(self) -> dict[str, Any]:
        return {
            "paths.dataDir": str(data_dir()),
            "logging.logDir": configured_text("logging.logDir", "PY_DESKTOP_TOOLS_LOG_DIR", str(data_dir() / "logs")),
            "paths.pluginDirs": os.pathsep.join(str(path) for path in plugin_dirs()),
            "developer.qmlHotReload": bool(configured_bool("developer.qmlHotReload", "PY_DESKTOP_QML_HOT_RELOAD", False)),
            "logging.console": bool(configured_bool("logging.console", "PY_DESKTOP_TOOLS_LOG_CONSOLE", not bool(getattr(sys, "frozen", False)))),
            "logging.consoleLevel": configured_text("logging.consoleLevel", "PY_DESKTOP_TOOLS_LOG_LEVEL", "WARNING"),
            "logging.fileLevel": configured_text("logging.fileLevel", "PY_DESKTOP_TOOLS_LOG_FILE_LEVEL", "WARNING"),
            "logging.qtLevel": configured_text("logging.qtLevel", "PY_DESKTOP_TOOLS_QT_LOG_LEVEL", "WARNING"),
            "logging.retentionDays": configured_int("logging.retentionDays", "PY_DESKTOP_TOOLS_LOG_RETENTION_DAYS", 7),
            "plugins.retentionMs": configured_int("plugins.retentionMs", "PY_DESKTOP_PLUGIN_RETENTION_MS", 300_000),
            "hotkeys.launcher": self._launcher_hotkey(),
            "hotkeys.windowsFallbackHook": configured_text("hotkeys.windowsFallbackHook", "PY_DESKTOP_TOOLS_HOTKEY_HOOK", ""),
        }

    @staticmethod
    def _default_data_dir() -> str:
        if sys.platform == "darwin":
            return str(Path.home() / "Library" / "Application Support" / "PyDesktopTools")
        if sys.platform == "win32":
            return str(Path(os.getenv("APPDATA", str(Path.home()))) / "PyDesktopTools")
        return str(Path.home() / ".local" / "share" / "py-desktop-tools")

    def _launcher_hotkey(self) -> str:
        services = getattr(self._platform, "_services", None)
        value = getattr(services, "default_launcher_hotkey", None)
        if value:
            return str(value)
        return configured_text("hotkeys.launcher", None, "Alt+Space")

    def _normalize_value(self, spec: SettingSpec, value):
        if spec.kind == "bool":
            return bool(parse_bool(value, bool(spec.default)))
        if spec.kind == "int":
            try:
                number = int(value)
            except (TypeError, ValueError):
                number = int(spec.default)
            if spec.minimum is not None:
                number = max(spec.minimum, number)
            if spec.maximum is not None:
                number = min(spec.maximum, number)
            return number
        if spec.kind == "choice":
            text = str(value or "").strip()
            if spec.options and text not in spec.options:
                return str(spec.default)
            return text
        if spec.kind in {"path", "pathList", "text"}:
            return str(value or "").strip()
        return value

    def _stored_value(self, spec: SettingSpec):
        if spec.key.startswith("clipboard."):
            return self._clipboard_config_value(spec.key)
        return self._settings.get(spec.key, None)

    def _source_for_spec(self, spec: SettingSpec) -> str:
        if spec.key.startswith("clipboard."):
            return "settings"
        return setting_source(spec.key, spec.env)

    def _clipboard_service(self) -> object | None:
        services = getattr(self._platform, "_services", None)
        service = getattr(services, "clipboard_service", None)
        if service is not None:
            return service
        service = getattr(self, "_clipboard", None)
        if service is not None:
            return service
        return None

    def _clipboard_config_value(self, key: str):
        store = self._clipboard_settings_store()
        mapped = _clipboard_config_key(key)
        service = self._clipboard_service()
        get_value = getattr(service, "get_config_value", None)
        if callable(get_value):
            return get_value(mapped)
        if store is not None:
            return store.get(mapped, DEFAULT_CLIPBOARD_CONFIG.get(mapped))
        return DEFAULT_CLIPBOARD_CONFIG.get(mapped)

    def _set_clipboard_config(self, key: str, value: object) -> bool:
        mapped = _clipboard_config_key(key)
        service = self._clipboard_service()
        set_value = getattr(service, "set_config_value", None)
        if callable(set_value):
            return bool(set_value(mapped, value))
        store = self._clipboard_settings_store()
        if store is not None:
            store.set(mapped, value)
            return True
        return False

    def _clipboard_settings_store(self) -> object | None:
        dict_store = getattr(self._storage, "dict_store", None)
        if not callable(dict_store):
            return None
        try:
            return dict_store("clipboard/settings", defaults=DEFAULT_CLIPBOARD_CONFIG)
        except Exception:
            return None

    @staticmethod
    def _source_text(source: str) -> str:
        if source == "env":
            return "环境变量"
        if source == "settings":
            return "设置文件"
        return "默认值"

    def _accessibility_status(self) -> dict:
        if self._permissions is None:
            return {"status": "unknown"}
        status_fn = getattr(self._permissions, "accessibility_status", None)
        if not callable(status_fn):
            return {"status": "unknown"}
        try:
            result = status_fn()
        except Exception:
            return {"status": "unknown"}
        data = getattr(result, "data", None)
        return data if isinstance(data, dict) else {"status": "unknown"}
