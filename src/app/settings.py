from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from threading import RLock
from typing import Any


SETTINGS_FILE_ENV = "PY_DESKTOP_TOOLS_SETTINGS_FILE"

_TRUE_VALUES = {"1", "true", "yes", "on", "always"}
_FALSE_VALUES = {"0", "false", "no", "off", "never"}
_MISSING = object()
_STORE: "AppSettingsStore | None" = None


class AppSettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or settings_file_path()
        self._lock = RLock()

    def all(self) -> dict[str, Any]:
        with self._lock:
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (FileNotFoundError, OSError, json.JSONDecodeError):
                return {}
            return data if isinstance(data, dict) else {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.all().get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            data = self.all()
            data[str(key)] = value
            self._write(data)

    def delete(self, key: str) -> None:
        with self._lock:
            data = self.all()
            if str(key) not in data:
                return
            del data[str(key)]
            self._write(data)

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def settings_file_path() -> Path:
    configured = os.getenv(SETTINGS_FILE_ENV, "").strip()
    if configured:
        return Path(configured).expanduser()
    return _default_settings_root() / "settings.json"


def get_app_settings_store() -> AppSettingsStore:
    global _STORE
    path = settings_file_path()
    if _STORE is None or _STORE.path != path:
        _STORE = AppSettingsStore(path)
    return _STORE


def configured_value(key: str, env_name: str | None = None, default: Any = None) -> Any:
    if env_name:
        value = os.getenv(env_name)
        if value is not None and str(value).strip() != "":
            return value
    value = get_app_settings_store().get(key, _MISSING)
    return default if value is _MISSING else value


def configured_text(key: str, env_name: str | None = None, default: str = "") -> str:
    value = configured_value(key, env_name, default)
    return "" if value is None else str(value)


def configured_int(key: str, env_name: str | None = None, default: int = 0) -> int:
    value = configured_value(key, env_name, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def configured_bool(
    key: str,
    env_name: str | None = None,
    default: bool | None = False,
) -> bool | None:
    value = configured_value(key, env_name, _MISSING)
    if value is _MISSING:
        return default
    return parse_bool(value, default)


def parse_bool(value: Any, default: bool | None = False) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in _TRUE_VALUES:
        return True
    if text in _FALSE_VALUES:
        return False
    return default


def setting_source(key: str, env_name: str | None = None) -> str:
    if env_name and os.getenv(env_name) is not None and str(os.getenv(env_name)).strip() != "":
        return "env"
    if key in get_app_settings_store().all():
        return "settings"
    return "default"


def _default_settings_root() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "PyDesktopTools"
    if sys.platform == "win32":
        return Path(os.getenv("APPDATA", str(Path.home()))) / "PyDesktopTools"
    return Path.home() / ".local" / "share" / "py-desktop-tools"
