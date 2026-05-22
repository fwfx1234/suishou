"""Lazy QtWebEngine initialization.

`from PySide6.QtWebEngineQuick import QtWebEngineQuick` alone loads Chromium
dylibs and increases idle RSS by ~46 MB on macOS. WebEngine is only used by
`remote_files`, so we defer import + initialize until that plugin is opened.
"""

from __future__ import annotations

from threading import Lock

from app.logging import get_logger

_initialized = False
_lock = Lock()


def ensure_webengine_initialized() -> None:
    """Import and initialize QtWebEngine on first use. Idempotent and thread-safe."""

    global _initialized
    if _initialized:
        return
    with _lock:
        if _initialized:
            return
        log = get_logger("app.webengine")
        try:
            from PySide6.QtWebEngineQuick import QtWebEngineQuick

            QtWebEngineQuick.initialize()
            _initialized = True
            log.info("webengine.initialized", "QtWebEngine 已按需初始化")
        except Exception as exc:
            log.error(
                "webengine.init_failed",
                "QtWebEngine 初始化失败",
                error=str(exc),
                errorType=type(exc).__name__,
            )
            raise


def is_webengine_initialized() -> bool:
    return _initialized
