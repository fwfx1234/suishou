__all__ = [
    "WindowsAppIndexer",
    "WindowsClipboardApi",
    "WindowsExternalLauncher",
    "WindowsHotkeyFactory",
    "WindowsSystemCommandProvider",
]


def __getattr__(name: str):
    if name == "WindowsAppIndexer":
        from .apps import WindowsAppIndexer

        return WindowsAppIndexer
    if name == "WindowsClipboardApi":
        from .clipboard import WindowsClipboardApi

        return WindowsClipboardApi
    if name == "WindowsExternalLauncher":
        from .external_launcher import WindowsExternalLauncher

        return WindowsExternalLauncher
    if name == "WindowsHotkeyFactory":
        from .hotkey import WindowsHotkeyFactory

        return WindowsHotkeyFactory
    if name == "WindowsSystemCommandProvider":
        from .system_commands import WindowsSystemCommandProvider

        return WindowsSystemCommandProvider
    raise AttributeError(name)
