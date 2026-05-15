from __future__ import annotations

from PySide6.QtCore import QObject, Slot

from app.paths import data_dir
from app.plugins.manifest_loader import load_all_plugin_manifests


class SystemSettingsViewModel(QObject):
    @Slot(result="QVariantMap")
    def diagnostics(self) -> dict:
        manifests = load_all_plugin_manifests()
        background = [item.id for item in manifests if item.activation == "background"]
        root = data_dir()
        return {
            "dataDir": str(root),
            "logDir": str(root / "logs"),
            "pluginCount": len(manifests),
            "backgroundPlugins": ", ".join(background) if background else "无",
        }
