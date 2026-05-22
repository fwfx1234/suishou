from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.plugins.manifest import CommandContribution, PluginManifest
from app.plugins.runtime import PluginContext
from app.plugins.session_manager import ManagedPluginSession, PluginSessionManager


def _make_manifest(plugin_id: str = "demo") -> PluginManifest:
    return PluginManifest(
        id=plugin_id,
        name=plugin_id,
        version="1",
        description="",
        icon="",
        entrypoint="runtime:create_runtime",
        qml_page="DemoPage.qml",
        context_property="demoVm",
        commands=[
            CommandContribution(
                id=f"{plugin_id}.open",
                title="Open",
                launch_mode="window",
            )
        ],
    )


class PluginSessionManagerUnloadTests(unittest.TestCase):
    def _make_manager(self, *, manifest: PluginManifest) -> tuple[PluginSessionManager, MagicMock, MagicMock]:
        qml_context = MagicMock()
        plugin_manager = MagicMock()
        plugin_manager.get_manifest.return_value = manifest
        plugin_context = PluginContext()
        manager = PluginSessionManager(qml_context, plugin_manager, plugin_context)
        return manager, qml_context, plugin_manager

    def test_unload_plugin_closes_session_and_clears_context(self) -> None:
        manifest = _make_manifest()
        manager, qml_context, plugin_manager = self._make_manager(manifest=manifest)
        session = MagicMock()
        session.manifest = manifest
        session.launch_mode = "window"
        record = ManagedPluginSession(
            plugin_id=manifest.id,
            session=session,
            state=SimpleNamespace(host="window"),
            context_names={"demoVm"},
            session_id="sess-1",
        )
        manager._sessions[manifest.id] = record

        manager.unload_plugin(manifest.id)

        session.close.assert_called_once()
        qml_context.setContextProperty.assert_any_call("demoVm", None)
        plugin_manager.close_runtime.assert_called_once_with(manifest.id)
        self.assertNotIn(manifest.id, manager._sessions)

    def test_retention_timeout_invokes_callback_instead_of_unload(self) -> None:
        manifest = _make_manifest()
        callback = MagicMock()
        qml_context = MagicMock()
        plugin_manager = MagicMock()
        plugin_manager.get_manifest.return_value = manifest
        manager = PluginSessionManager(
            qml_context,
            plugin_manager,
            PluginContext(),
            on_retention_expired=callback,
        )
        session = MagicMock()
        session.manifest = manifest
        session.launch_mode = "window"
        state = SimpleNamespace(host="window")
        manager._sessions[manifest.id] = ManagedPluginSession(
            plugin_id=manifest.id,
            session=session,
            state=state,
            context_names={"demoVm"},
            session_id="sess-1",
        )

        manager._handle_retention_timeout(manifest.id)

        callback.assert_called_once_with(manifest.id, state)
        session.close.assert_not_called()

    def test_handle_retention_timeout_without_callback_unloads(self) -> None:
        manifest = _make_manifest()
        manager, _qml, plugin_manager = self._make_manager(manifest=manifest)
        session = MagicMock()
        session.manifest = manifest
        session.launch_mode = "window"
        manager._sessions[manifest.id] = ManagedPluginSession(
            plugin_id=manifest.id,
            session=session,
            state=SimpleNamespace(host="window"),
            context_names=set(),
            session_id="sess-1",
        )

        manager._handle_retention_timeout(manifest.id)

        session.close.assert_called_once()
        plugin_manager.close_runtime.assert_called_once_with(manifest.id)
        self.assertNotIn(manifest.id, manager._sessions)


if __name__ == "__main__":
    unittest.main()
