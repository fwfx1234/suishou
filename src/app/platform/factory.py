from __future__ import annotations

import platform
import sys

from app.commands.dynamic_command_registry import DynamicCommandRegistry
from app.settings import configured_text
from app.storage import StorageManager

from .common.dynamic_commands import PlatformCommandApiFactory
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
        from app.services.clipboard.backends.win32_backend import Win32ClipboardBackend

        from .windows.apps import WindowsAppIndexer
        from .windows.clipboard import WindowsClipboardApi
        from .windows.external_launcher import WindowsExternalLauncher
        from .windows.hotkey import WindowsHotkeyFactory
        from .windows.notifications import WindowsNotificationApi
        from .windows.paths import WindowsAppPaths
        from .windows.permissions import WindowsPermissionApi
        from .windows.system_commands import WindowsSystemCommandProvider
        from .windows.tray_appearance import WindowsTrayAppearance
        from .windows.windowing import WindowsWindowingApi

        return PlatformServices(
            info=PlatformInfo("windows", "Windows", version=version, is_packaged=is_packaged),
            default_launcher_hotkey=configured_text("hotkeys.launcher", None, "Alt+Space"),
            default_clipboard_hotkey="Alt+V",
            paths=WindowsAppPaths(),
            hotkey_factory=WindowsHotkeyFactory(),
            app_indexer=WindowsAppIndexer(),
            external_launcher=WindowsExternalLauncher(),
            system_commands=WindowsSystemCommandProvider(),
            clipboard=WindowsClipboardApi(),
            dialogs=QtDialogApi(),
            screen=QtScreenApi(),
            storage_factory=storage_factory,
            dynamic_command_api_factory=command_api_factory,
            permissions=WindowsPermissionApi(),
            tray_appearance=WindowsTrayAppearance(),
            windowing=WindowsWindowingApi(),
            notifications=WindowsNotificationApi(),
            clipboard_subscriber=Win32ClipboardBackend(),
        )
    if sys.platform == "darwin":
        from .macos.apps import MacOSAppIndexer
        from .macos.clipboard import MacOSClipboardApi
        from .macos.external_launcher import MacOSExternalLauncher
        from .macos.hotkey import MacHotkeyFactory
        from .macos.notifications import MacOSNotificationApi
        from .macos.paths import MacOSAppPaths
        from .macos.permissions import MacOSPermissionApi
        from .macos.system_commands import MacOSSystemCommandProvider
        from .macos.tray_appearance import MacOSTrayAppearance
        from .macos.windowing import MacOSWindowingApi

        try:
            from app.services.clipboard.backends.macos_backend import MacOSClipboardBackend

            clipboard_subscriber = MacOSClipboardBackend()
        except Exception:
            from app.services.clipboard.backends.pyperclip_backend import PyperclipClipboardBackend

            clipboard_subscriber = PyperclipClipboardBackend()

        return PlatformServices(
            info=PlatformInfo("macos", "macOS", version=version, is_packaged=is_packaged),
            default_launcher_hotkey=configured_text("hotkeys.launcher", None, "Alt+Space"),
            default_clipboard_hotkey="Alt+V",
            paths=MacOSAppPaths(),
            hotkey_factory=MacHotkeyFactory(),
            app_indexer=MacOSAppIndexer(),
            external_launcher=MacOSExternalLauncher(),
            system_commands=MacOSSystemCommandProvider(),
            clipboard=MacOSClipboardApi(),
            dialogs=QtDialogApi(),
            screen=QtScreenApi(),
            storage_factory=storage_factory,
            dynamic_command_api_factory=command_api_factory,
            permissions=MacOSPermissionApi(),
            tray_appearance=MacOSTrayAppearance(),
            windowing=MacOSWindowingApi(),
            notifications=MacOSNotificationApi(),
            clipboard_subscriber=clipboard_subscriber,
        )
    from app.services.clipboard.backends.noop_backend import NoopClipboardBackend

    from .noop.apps import NoopAppIndexer
    from .noop.clipboard import NoopClipboardApi
    from .noop.external_launcher import NoopExternalLauncher
    from .noop.hotkey import NoopHotkeyFactory
    from .noop.notifications import NoopNotificationApi
    from .noop.paths import NoopAppPaths
    from .noop.permissions import NoopPermissionApi
    from .noop.system_commands import NoopSystemCommandProvider
    from .noop.tray_appearance import NoopTrayAppearance
    from .noop.windowing import NoopWindowingApi

    return PlatformServices(
        info=PlatformInfo("unknown", platform.system() or "Unknown", version=version, is_packaged=is_packaged),
        default_launcher_hotkey=configured_text("hotkeys.launcher", None, "Alt+Space"),
        default_clipboard_hotkey="Alt+V",
        paths=NoopAppPaths(),
        hotkey_factory=NoopHotkeyFactory(),
        app_indexer=NoopAppIndexer(),
        external_launcher=NoopExternalLauncher(),
        system_commands=NoopSystemCommandProvider(),
        clipboard=NoopClipboardApi(),
        dialogs=QtDialogApi(),
        screen=QtScreenApi(),
        storage_factory=storage_factory,
        dynamic_command_api_factory=command_api_factory,
        permissions=NoopPermissionApi(),
        tray_appearance=NoopTrayAppearance(),
        windowing=NoopWindowingApi(),
        notifications=NoopNotificationApi(),
        clipboard_subscriber=NoopClipboardBackend(),
    )
