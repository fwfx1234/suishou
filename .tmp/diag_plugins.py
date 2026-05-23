"""Diagnose plugin QML loading via real app bootstrap."""
import os
import sys
os.environ.setdefault("PY_DESKTOP_TOOLS_LOG_CONSOLE", "1")
os.environ.setdefault("PY_DESKTOP_TOOLS_LOG_LEVEL", "WARNING")

from pathlib import Path
from PySide6.QtCore import QUrl, QObject, QtMsgType, qInstallMessageHandler
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineQuick import QtWebEngineQuick


qml_messages: list[str] = []


def qt_msg(mode, ctx, message):
    text = f"[{mode.name}] {message}"
    if ctx and getattr(ctx, "file", None):
        text += f"  @ {ctx.file}:{ctx.line}"
    qml_messages.append(text)


qInstallMessageHandler(qt_msg)

QQuickStyle.setStyle("Basic")
QtWebEngineQuick.initialize()
app = QApplication([])

from app.app_bootstrap import ApplicationBootstrapper
from app.logging import init_logging, get_logger

init_logging(app_name="diag", app_version="1.0.0", level="WARNING", console=False, retention_days=1)
log = get_logger("diag")
ctx = ApplicationBootstrapper(app, log).build()


def diag_plugin(plugin_id: str):
    print(f"\n=== {plugin_id} ===")
    m = next((x for x in ctx.manifests if x.id == plugin_id), None)
    if not m:
        print("  manifest not found")
        return
    cmd = m.primary_command.id
    try:
        sess = ctx.plugin_manager.open_session(plugin_id, ctx.plugin_context, command_id=cmd, input_text="", payload={}, trace_id="")
    except Exception as exc:
        print(f"  open_session FAILED: {type(exc).__name__}: {exc}")
        return
    if sess is None:
        print("  session is None")
        return
    bound = ctx.session_manager._bind_session_context(sess)
    print(f"  context names: {bound}")
    page = sess.qml_page()
    print(f"  qml_page: {page}")
    qml_messages.clear()
    try:
        if page:
            comp = QQmlComponent(ctx.engine, QUrl(page))
            if comp.status() != QQmlComponent.Status.Ready:
                print(f"  COMPONENT ERROR: {comp.errorString()[:300]}")
            else:
                obj = comp.create()
                app.processEvents()
                if obj is None:
                    print("  obj is None after create()")
                else:
                    print("  OK")
                    obj.deleteLater()
    except Exception as exc:
        print(f"  EXC: {type(exc).__name__}: {exc}")
    for msg in qml_messages[:15]:
        print(f"  {msg}")
    try:
        ctx.session_manager.unload_plugin(plugin_id)
        ctx.plugin_manager.close_runtime(plugin_id)
    except Exception as exc:
        print(f"  cleanup err: {exc}")


for plugin_id in [
    "api-test",
    "remote-files",
    "qr-code",
    "clipboard",
    "json-parser",
    "image-compress",
    "download",
    "packet-capture",
    "qml-demo",
    "system-settings",
]:
    diag_plugin(plugin_id)
