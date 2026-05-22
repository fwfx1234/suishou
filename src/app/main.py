"""Application entry point for the uTools-like launcher runtime."""

from __future__ import annotations

import sys
from time import perf_counter
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtQuick import QQuickWindow
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from .app_runtime import ApplicationRuntime
from .logging import get_logger, init_logging, install_qt_message_handler
from .settings import configured_bool, configured_int, configured_text
from .version import get_app_version

LOG_CONSOLE_ENVS = ("SUISHOU_LOG_CONSOLE", "PY_DESKTOP_TOOLS_LOG_CONSOLE")
LOG_LEVEL_ENVS = ("SUISHOU_LOG_LEVEL", "PY_DESKTOP_TOOLS_LOG_LEVEL")
LOG_RETENTION_ENVS = ("SUISHOU_LOG_RETENTION_DAYS", "PY_DESKTOP_TOOLS_LOG_RETENTION_DAYS")


def _first_available_font(candidates: list[str]) -> str:
    for family in candidates:
        if QFontDatabase.hasFamily(family):
            return family
    return QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont).family()


def _configure_fonts(qt_app: QApplication) -> None:
    ui_family = _first_available_font([
        "PingFang SC",
        "Hiragino Sans GB",
        "Microsoft YaHei UI",
        "Segoe UI",
        "Microsoft YaHei",
    ])
    mono_family = _first_available_font([
        "SF Mono",
        "Menlo",
        "Consolas",
        "Cascadia Mono",
        "Microsoft YaHei UI",
    ])

    QFont.insertSubstitution("IBM Plex Sans", ui_family)
    QFont.insertSubstitution("JetBrains Mono", mono_family)
    QQuickWindow.setTextRenderType(QQuickWindow.TextRenderType.NativeTextRendering)

    app_font = QFont(ui_family)
    app_font.setPointSize(9)
    app_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app_font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    qt_app.setFont(app_font)


def _console_logging_enabled() -> bool:
    configured = configured_bool("logging.console", LOG_CONSOLE_ENVS, None)
    if configured is not None:
        return configured
    return not bool(getattr(sys, "frozen", False))


def main() -> int:
    app_started_at = perf_counter()
    console_logging = _console_logging_enabled()
    logging_started_at = perf_counter()
    logging_manager = init_logging(
        app_name="suishou",
        app_version=get_app_version(),
        level=configured_text("logging.consoleLevel", LOG_LEVEL_ENVS, "WARNING"),
        console=console_logging,
        retention_days=configured_int("logging.retentionDays", LOG_RETENTION_ENVS, 7),
    )
    logging_elapsed_ms = int((perf_counter() - logging_started_at) * 1000)
    log = get_logger("app.main")
    qt_message_started_at = perf_counter()
    install_qt_message_handler()
    qt_message_elapsed_ms = int((perf_counter() - qt_message_started_at) * 1000)
    style_started_at = perf_counter()
    QQuickStyle.setStyle("Basic")
    style_elapsed_ms = int((perf_counter() - style_started_at) * 1000)
    qt_app_started_at = perf_counter()
    qt_app = QApplication(sys.argv)
    qt_app_elapsed_ms = int((perf_counter() - qt_app_started_at) * 1000)
    fonts_started_at = perf_counter()
    _configure_fonts(qt_app)
    fonts_elapsed_ms = int((perf_counter() - fonts_started_at) * 1000)
    qt_app.setQuitOnLastWindowClosed(False)
    log.info(
        "app.start",
        "应用启动",
        platform=sys.platform,
        cwd=str(Path.cwd()),
        appVersion=get_app_version(),
        logDir=str(logging_manager.log_dir),
        consoleLogging=console_logging,
        loggingElapsedMs=logging_elapsed_ms,
        qtMessageHandlerElapsedMs=qt_message_elapsed_ms,
        styleElapsedMs=style_elapsed_ms,
        qtAppElapsedMs=qt_app_elapsed_ms,
        fontsElapsedMs=fonts_elapsed_ms,
        elapsedMs=int((perf_counter() - app_started_at) * 1000),
    )
    return ApplicationRuntime(qt_app, log).run()


if __name__ == "__main__":
    raise SystemExit(main())
