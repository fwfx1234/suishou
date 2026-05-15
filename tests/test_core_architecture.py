from __future__ import annotations

from pathlib import Path
import os
import sys
import tempfile
import unittest
import logging
from threading import Event
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.commands.command_context import CommandContextMatcher
from app.commands.command_index_db import CommandIndexDb
from app.commands.command_launcher import CommandLauncher
from app.commands.context import build_launcher_context
from app.commands.ranker import CommandRanker
from app.commands.usage_service import CommandUsageService
from app.concurrency import PythonTaskRunner
from app.hotkey_coordinator import HotkeyCoordinator
from app.logging.manager import LoggingManager
from app.platform.services import PlatformServices
from app.plugins.manifest import ContextMatcher
from app.plugins.manifest import CommandContribution, PluginManifest
from app.plugins.session_state import (
    PluginSessionState,
    active_state,
    reactivate_state,
    retained_state,
)
from app.plugins.service_registry import ServiceRegistry
from app.services.clipboard.service import ClipboardService
from app.storage import StorageManager


class CommandRankingTests(unittest.TestCase):
    def test_ranker_matches_title_keyword_and_pinyin_initial(self) -> None:
        self.assertEqual(CommandRanker.score("json", "JSON 解析", ["jq"], "")[0], 90)
        self.assertEqual(CommandRanker.score("jq", "JSON 解析", ["jq"], "")[0], 85)
        self.assertGreaterEqual(CommandRanker.score("j", "JSON 解析", [], "")[0], 70)

    def test_context_matcher_applies_prefix_and_input_reasons(self) -> None:
        context = build_launcher_context("api https://example.com", {"api"})
        score, reasons = CommandContextMatcher.apply_context(
            0,
            context,
            ["api"],
            [ContextMatcher(source="input", kind="url", boost=120)],
        )

        self.assertEqual(score, 360)
        self.assertEqual(reasons, ["prefix:api", "input:url"])
        self.assertEqual(
            CommandContextMatcher.launch_input_policy(0, context, ["api"], reasons),
            ("", "command", True),
        )

    def test_context_matcher_passes_content_for_matcher_launch(self) -> None:
        context = build_launcher_context("https://example.com", {"api"})
        score, reasons = CommandContextMatcher.apply_context(
            0,
            context,
            [],
            [ContextMatcher(source="input", kind="url", boost=120)],
        )

        self.assertEqual(score, 120)
        self.assertEqual(reasons, ["input:url"])
        self.assertEqual(
            CommandContextMatcher.launch_input_policy(0, context, [], reasons),
            ("https://example.com", "content", True),
        )


class StorageTests(unittest.TestCase):
    def test_database_dict_store_persists_namespace_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = StorageManager(Path(tmp))
            settings = storage.dict_store("plugin/settings", defaults={"enabled": True})
            settings["limit"] = 3

            reopened = storage.dict_store("plugin/settings")
            other = storage.dict_store("other/settings", defaults={"limit": 9})

            self.assertTrue(reopened.loaded_from_existing_store)
            self.assertEqual(reopened.get("enabled"), True)
            self.assertEqual(reopened.get("limit"), 3)
            self.assertEqual(other.get("limit"), 9)
            self.assertEqual(settings.path.name, "dict_store.db")


class CommandIndexTests(unittest.TestCase):
    def test_command_index_updates_apps_without_dropping_existing_icon(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = CommandIndexDb(StorageManager(Path(tmp)).database("command_index.db"))
            try:
                db.sync_apps(
                    [
                        {
                            "platform": "windows",
                            "name": "Foo App",
                            "launch_path": "foo.lnk",
                            "bundle_id": "",
                            "icon_path": "old.png",
                        }
                    ]
                )
                db.sync_apps(
                    [
                        {
                            "platform": "windows",
                            "name": "Foo App",
                            "launch_path": "foo.lnk",
                            "bundle_id": "",
                            "icon_path": "",
                        }
                    ]
                )

                self.assertEqual(db.search_apps("Foo")[0]["iconPath"], "old.png")

                db.record_launch("plugin:foo")
                db.record_launch("plugin:foo")
                self.assertEqual(db.usage_map()["plugin:foo"][0], 2)
            finally:
                db.close()


class CommandUsageServiceTests(unittest.TestCase):
    def test_usage_recording_is_best_effort(self) -> None:
        class BrokenIndex:
            def usage_map(self):
                raise OSError("disk I/O error")

            def record_launch(self, key: str) -> None:
                raise OSError(f"disk I/O error: {key}")

        service = CommandUsageService(BrokenIndex())  # type: ignore[arg-type]

        self.assertEqual(service.usage_map(), {})
        service.record_plugin_launch("json-parser")
        service.record_item_launch({"usageKey": "plugin:json-parser"})

    def test_external_launch_ignores_usage_record_failure(self) -> None:
        class BrokenIndex:
            def record_launch(self, key: str) -> None:
                raise OSError(f"disk I/O error: {key}")

        class Result:
            ok = True
            code = ""
            message = ""

        class ExternalLauncher:
            def launch_system_action(self, action: str) -> Result:
                self.action = action
                return Result()

            def launch_app(self, app: dict) -> Result:
                self.app = app
                return Result()

        class Platform:
            external_launcher = ExternalLauncher()

        launcher = CommandLauncher(BrokenIndex(), Platform())  # type: ignore[arg-type]

        self.assertEqual(
            launcher.launch_external_item("system:lock-screen", "system", {"action": "lock", "name": "Lock"}),
            "Lock",
        )
        self.assertEqual(
            launcher.launch_external_item("app:demo", "app", {"launchPath": "demo.lnk", "name": "Demo"}),
            "Demo",
        )


class ServiceRegistryTests(unittest.TestCase):
    def test_registry_exposes_typed_core_services(self) -> None:
        registry = ServiceRegistry()
        platform = object()
        storage = object()
        clipboard = object()

        registry.platform = platform
        registry.storage = storage
        registry.clipboard = clipboard

        self.assertIs(registry.require_platform(), platform)
        self.assertIs(registry.require_storage(), storage)
        self.assertIs(registry.clipboard, clipboard)
        self.assertIs(registry.get_typed("storage", object), storage)

        registry.platform = None
        with self.assertRaises(RuntimeError):
            registry.require_platform()


class PluginSessionStateTests(unittest.TestCase):
    def test_session_state_helpers_make_host_transitions_explicit(self) -> None:
        self.assertEqual(active_state("inline_view"), PluginSessionState.ACTIVE_INLINE)
        self.assertEqual(active_state("list"), PluginSessionState.ACTIVE_LIST)
        self.assertEqual(active_state("window"), PluginSessionState.ACTIVE_WINDOW)
        self.assertEqual(active_state("inline_view", "window"), PluginSessionState.ACTIVE_WINDOW)

        retained = retained_state("inline_view", "inline")
        self.assertEqual(retained, PluginSessionState.RETAINED_INLINE)
        self.assertTrue(retained.retained)
        self.assertEqual(retained.host, "inline")

        self.assertEqual(
            reactivate_state(PluginSessionState.RETAINED_WINDOW, "inline_view"),
            PluginSessionState.ACTIVE_WINDOW,
        )


class ClipboardServiceTests(unittest.TestCase):
    def test_latest_context_item_prefers_captured_item(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_data_dir = os.environ.get("PY_DESKTOP_TOOLS_DATA_DIR")
            old_log_dir = os.environ.get("PY_DESKTOP_TOOLS_LOG_DIR")
            os.environ["PY_DESKTOP_TOOLS_DATA_DIR"] = str(Path(tmp) / "data")
            os.environ["PY_DESKTOP_TOOLS_LOG_DIR"] = str(ROOT / ".tmp" / "test_logs")
            storage = StorageManager(Path(tmp))
            try:
                service = ClipboardService(
                    storage.database("clipboard.db"),
                    settings_store=storage.dict_store("clipboard/settings"),
                )
                service.store.capture_draft(
                    type(
                        "Draft",
                        (),
                        {
                            "item_type": "text",
                            "content": "hello",
                            "preview": "hello",
                            "metadata": {},
                            "image_bytes": None,
                        },
                    )()
                )

                item = service.latest_context_item()
                self.assertIsNotNone(item)
                self.assertEqual(item["content"], "hello")
            finally:
                if "service" in locals():
                    service.close()
                if old_data_dir is None:
                    os.environ.pop("PY_DESKTOP_TOOLS_DATA_DIR", None)
                else:
                    os.environ["PY_DESKTOP_TOOLS_DATA_DIR"] = old_data_dir
                if old_log_dir is None:
                    os.environ.pop("PY_DESKTOP_TOOLS_LOG_DIR", None)
                else:
                    os.environ["PY_DESKTOP_TOOLS_LOG_DIR"] = old_log_dir


class PythonTaskRunnerTests(unittest.TestCase):
    def test_runner_handles_success_error_and_cancel(self) -> None:
        runner = PythonTaskRunner(max_workers=1, thread_name_prefix="test-task")
        try:
            success = Event()
            errors: list[str] = []
            results: list[object] = []

            runner.start(
                lambda: "ok",
                on_success=lambda value: (results.append(value), success.set()),
                on_error=lambda exc: errors.append(str(exc)),
            )
            self.assertTrue(success.wait(2))
            self.assertEqual(results, ["ok"])
            self.assertEqual(errors, [])

            failed = Event()
            runner.start(
                lambda: (_ for _ in ()).throw(RuntimeError("boom")),
                on_error=lambda exc: (errors.append(str(exc)), failed.set()),
            )
            self.assertTrue(failed.wait(2))
            self.assertIn("boom", errors[-1])

            cancelled_called = Event()
            handle = runner.start(
                lambda task: "cancelled" if task.cancel_event.wait(1) else "done",
                on_success=lambda _value: cancelled_called.set(),
            )
            runner.cancel(handle.id)
            self.assertFalse(cancelled_called.wait(0.2))
        finally:
            runner.shutdown(wait=True)


class LoggingManagerTests(unittest.TestCase):
    def test_plugin_log_handler_creates_nested_directory(self) -> None:
        old_handlers = list(logging.getLogger().handlers)
        with tempfile.TemporaryDirectory() as tmp:
            manager = LoggingManager(
                app_name="test",
                app_version="test",
                log_dir=Path(tmp) / "logs",
                console=False,
            )
            try:
                logger = manager.for_plugin("api-test")
                logger.info("probe", "probe")
                self.assertTrue((Path(tmp) / "logs" / "plugins").is_dir())
                self.assertTrue((Path(tmp) / "logs" / "plugins" / "api-test.log").exists())
            finally:
                manager.shutdown()
                root = logging.getLogger()
                for handler in list(root.handlers):
                    root.removeHandler(handler)
                for handler in old_handlers:
                    root.addHandler(handler)


class WindowsHotkeyTests(unittest.TestCase):
    def test_windows_hotkey_parses_common_sequences(self) -> None:
        from app.platform.windows.hotkey import MOD_ALT, MOD_CONTROL, MOD_SHIFT, parse_hotkey

        self.assertEqual(parse_hotkey("Alt+Space"), (MOD_ALT, 0x20))
        self.assertEqual(parse_hotkey("Ctrl+Shift+F12"), (MOD_CONTROL | MOD_SHIFT, 0x7B))
        self.assertIsNone(parse_hotkey("Alt"))

    def test_windows_hotkey_fallback_env_controls_hook(self) -> None:
        from app.platform.windows.hotkey import WinHotkeyManager

        manager = WinHotkeyManager(hotkey="Alt+Space")
        manager._native_registered = True
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PY_DESKTOP_TOOLS_HOTKEY_HOOK", None)
            self.assertTrue(manager._should_enable_fallback())
        manager = WinHotkeyManager(hotkey="Ctrl+Alt+K", hotkey_id=9)
        manager._native_registered = True
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PY_DESKTOP_TOOLS_HOTKEY_HOOK", None)
            self.assertFalse(manager._should_enable_fallback())
        with patch.dict(os.environ, {"PY_DESKTOP_TOOLS_HOTKEY_HOOK": "1"}, clear=False):
            self.assertTrue(manager._should_enable_fallback())
        manager._native_registered = False
        with patch.dict(os.environ, {"PY_DESKTOP_TOOLS_HOTKEY_HOOK": "0"}, clear=False):
            self.assertFalse(manager._should_enable_fallback())
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PY_DESKTOP_TOOLS_HOTKEY_HOOK", None)
            self.assertTrue(manager._should_enable_fallback())


class _FakeSignal:
    def connect(self, callback) -> None:
        self.callback = callback


class _FakeHotkeyManager:
    def __init__(self) -> None:
        self.hotkeyPressed = _FakeSignal()
        self.unregistered = 0
        self.registered: list[str] = []

    def register(self, hotkey: str | None = None) -> bool:
        self.registered.append(hotkey or "")
        return True

    def unregister(self) -> None:
        self.unregistered += 1


class _FakeHotkeyFactory:
    def __init__(self) -> None:
        self.managers: list[_FakeHotkeyManager] = []

    def create(self, *, parent: object | None, hotkey: str, hotkey_id: int) -> _FakeHotkeyManager:
        del parent, hotkey, hotkey_id
        manager = _FakeHotkeyManager()
        self.managers.append(manager)
        return manager

    def install_filter(self, app: object, manager: object) -> object | None:
        del app, manager
        return None


class _EmptyCommands:
    def commands(self) -> list:
        return []


class HotkeyCoordinatorTests(unittest.TestCase):
    def test_refresh_plugin_hotkeys_unregisters_existing_once(self) -> None:
        factory = _FakeHotkeyFactory()
        services = PlatformServices(
            info=object(),
            default_launcher_hotkey="Alt+Space",
            default_clipboard_hotkey="Alt+V",
            paths=object(),
            hotkey_factory=factory,
            app_indexer=object(),
            external_launcher=object(),
            system_commands=_EmptyCommands(),
            clipboard=object(),
            dialogs=object(),
            screen=object(),
            storage_factory=object(),
            dynamic_command_api_factory=object(),
            permissions=object(),
        )
        coordinator = HotkeyCoordinator(services, object())
        manifest = PluginManifest(
            id="demo",
            name="Demo",
            version="1",
            description="",
            icon="",
            entrypoint="runtime:create_runtime",
            qml_page="Demo.qml",
            commands=[CommandContribution(id="demo.open", title="Demo", hotkey="Ctrl+D")],
        )

        coordinator.refresh_plugin_hotkeys([manifest])
        first_plugin_manager = factory.managers[-1]
        coordinator.refresh_plugin_hotkeys([])

        self.assertEqual(first_plugin_manager.unregistered, 1)


if __name__ == "__main__":
    unittest.main()
