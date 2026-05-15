from __future__ import annotations

from dataclasses import dataclass

from .api import PlatformApi
from .models import PlatformInfo
from .protocols import (
    AppIndexerProtocol,
    ClipboardApiProtocol,
    DialogApiProtocol,
    DynamicCommandApiFactoryProtocol,
    ExternalLauncherProtocol,
    HotkeyFactoryProtocol,
    PermissionApiProtocol,
    ScreenApiProtocol,
    StorageFactoryProtocol,
    SystemCommandProviderProtocol,
)


@dataclass(slots=True)
class PlatformServices:
    info: PlatformInfo
    default_launcher_hotkey: str
    default_clipboard_hotkey: str
    paths: object
    hotkey_factory: HotkeyFactoryProtocol
    app_indexer: AppIndexerProtocol
    external_launcher: ExternalLauncherProtocol
    system_commands: SystemCommandProviderProtocol
    clipboard: ClipboardApiProtocol
    dialogs: DialogApiProtocol
    screen: ScreenApiProtocol
    storage_factory: StorageFactoryProtocol
    dynamic_command_api_factory: DynamicCommandApiFactoryProtocol
    permissions: PermissionApiProtocol

    def create_api(self, *, plugin_id: str = "") -> PlatformApi:
        return PlatformApi(self, plugin_id=plugin_id)
