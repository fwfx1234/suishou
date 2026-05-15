from __future__ import annotations

import platform
import sys

from app import paths as app_paths
from app.commands.dynamic_command_registry import DynamicCommandRegistry
from app.storage import StorageManager

from .common.dynamic_commands import PlatformCommandApiFactory
from .common.permissions import DefaultPermissionApi
from .common.storage import PlatformStorageFactory
from .dialogs import QtDialogApi
from .models import PlatformInfo
from .screen import QtScreenApi
from .services import PlatformServices


def create_platform_services(
    app: object | None = None,
    *,
    storage: StorageManager | None = None,
    dynamic_commands: DynamicCommandRegistry | None = None,
) -> PlatformServices:
    del app
    storage = storage or StorageManager()
    dynamic_commands = dynamic_commands or DynamicCommandRegistry()
    storage_factory = PlatformStorageFactory(storage)
    command_api_factory = PlatformCommandApiFactory(dynamic_commands)
    is_packaged = bool(getattr(sys, "frozen", False))
    version = platform.mac_ver()[0] if sys.platform == "darwin" else platform.version()

    if sys.platform == "win32":
        from .windows.apps import WindowsAppIndexer
        from .windows.clipboard import WindowsClipboardApi
        from .windows.external_launcher import WindowsExternalLauncher
        from .windows.hotkey import WindowsHotkeyFactory
        from .windows.system_commands import WindowsSystemCommandProvider

        return PlatformServices(
            info=PlatformInfo("windows", "Windows", version=version, is_packaged=is_packaged),
            default_launcher_hotkey="Alt+Space",
            default_clipboard_hotkey="Alt+V",
            paths=app_paths,
            hotkey_factory=WindowsHotkeyFactory(),
            app_indexer=WindowsAppIndexer(),
            external_launcher=WindowsExternalLauncher(),
            system_commands=WindowsSystemCommandProvider(),
            clipboard=WindowsClipboardApi(),
            dialogs=QtDialogApi(),
            screen=QtScreenApi(),
            storage_factory=storage_factory,
            dynamic_command_api_factory=command_api_factory,
            permissions=DefaultPermissionApi(),
        )
    if sys.platform == "darwin":
        from .macos.apps import MacOSAppIndexer
        from .macos.clipboard import MacOSClipboardApi
        from .macos.external_launcher import MacOSExternalLauncher
        from .macos.hotkey import MacHotkeyFactory
        from .macos.system_commands import MacOSSystemCommandProvider

        return PlatformServices(
            info=PlatformInfo("macos", "macOS", version=version, is_packaged=is_packaged),
            default_launcher_hotkey="Alt+Space",
            default_clipboard_hotkey="Alt+V",
            paths=app_paths,
            hotkey_factory=MacHotkeyFactory(),
            app_indexer=MacOSAppIndexer(),
            external_launcher=MacOSExternalLauncher(),
            system_commands=MacOSSystemCommandProvider(),
            clipboard=MacOSClipboardApi(),
            dialogs=QtDialogApi(),
            screen=QtScreenApi(),
            storage_factory=storage_factory,
            dynamic_command_api_factory=command_api_factory,
            permissions=DefaultPermissionApi(),
        )
    from .noop.apps import NoopAppIndexer
    from .noop.clipboard import NoopClipboardApi
    from .noop.external_launcher import NoopExternalLauncher
    from .noop.hotkey import NoopHotkeyFactory
    from .noop.system_commands import NoopSystemCommandProvider

    return PlatformServices(
        info=PlatformInfo("unknown", platform.system() or "Unknown", version=version, is_packaged=is_packaged),
        default_launcher_hotkey="Alt+Space",
        default_clipboard_hotkey="Alt+V",
        paths=app_paths,
        hotkey_factory=NoopHotkeyFactory(),
        app_indexer=NoopAppIndexer(),
        external_launcher=NoopExternalLauncher(),
        system_commands=NoopSystemCommandProvider(),
        clipboard=NoopClipboardApi(),
        dialogs=QtDialogApi(),
        screen=QtScreenApi(),
        storage_factory=storage_factory,
        dynamic_command_api_factory=command_api_factory,
        permissions=DefaultPermissionApi(),
    )
