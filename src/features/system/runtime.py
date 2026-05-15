from __future__ import annotations

from app.plugins.runtime import SimpleQmlRuntime

from .view_model import SystemSettingsViewModel


def create_settings_runtime() -> SimpleQmlRuntime:
    return SimpleQmlRuntime(lambda _ctx: SystemSettingsViewModel())


def create_about_runtime() -> SimpleQmlRuntime:
    return SimpleQmlRuntime(lambda _ctx: None)
