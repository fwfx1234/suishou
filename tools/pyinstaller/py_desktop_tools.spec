# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


ROOT = Path.cwd()
APP_NAME = "PyDesktopTools"
APP_BUNDLE_ID = "com.fwfx1234.pydesktoptools"

ICON_DIR = ROOT / "assets" / "app_icon"
ICNS_PATH = ICON_DIR / "app_icon.icns"
ICO_PATH = ICON_DIR / "app_icon.ico"
PNG_PATH = ICON_DIR / "app_icon.png"


def _exe_icon():
    import sys
    if sys.platform == "darwin" and ICNS_PATH.exists():
        return str(ICNS_PATH)
    if sys.platform == "win32" and ICO_PATH.exists():
        return str(ICO_PATH)
    if PNG_PATH.exists():
        return str(PNG_PATH)
    return None


def _bundle_icon():
    return str(ICNS_PATH) if ICNS_PATH.exists() else None

EXCLUDED_QT_MODULES = {
    "Qt3D",
    "Qt3DAnimation",
    "Qt3DCore",
    "Qt3DExtras",
    "Qt3DInput",
    "Qt3DLogic",
    "Qt3DQuick",
    "Qt3DQuickAnimation",
    "Qt3DQuickExtras",
    "Qt3DQuickInput",
    "Qt3DQuickRender",
    "Qt3DRender",
    "QtCharts",
    "QtChartsQml",
    "QtDataVisualization",
    "QtDataVisualizationQml",
    "QtGraphs",
    "QtGraphsWidgets",
    "QtLocation",
    "QtMultimedia",
    "QtMultimediaQuick",
    "QtMultimediaWidgets",
    "QtPdf",
    "QtPdfQuick",
    "QtPdfWidgets",
    "QtPositioning",
    "QtPositioningQuick",
    "QtQuick3D",
    "QtQuick3DAssetUtils",
    "QtQuick3DEffects",
    "QtQuick3DHelpers",
    "QtQuick3DHelpersImpl",
    "QtQuick3DParticles",
    "QtQuick3DRuntimeRender",
    "QtQuick3DUtils",
    "QtQuick3DXr",
    "QtRemoteObjects",
    "QtScxml",
    "QtSensors",
    "QtSensorsQuick",
    "QtSpatialAudio",
    "QtTextToSpeech",
    "QtVirtualKeyboard",
    "QtWebChannel",
    "QtWebEngine",
    "QtWebEngineCore",
    "QtWebEngineQuick",
    "QtWebEngineQuickDelegatesQml",
    "QtWebEngineWidgets",
    "QtWebSockets",
}


def tree_data(root: Path, prefix: str) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for path in root.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        if any(part in {".pytest_cache", ".mypy_cache", ".ruff_cache"} for part in path.parts):
            continue
        if path.name == ".DS_Store":
            continue
        if path.name.endswith((".log", ".tmp")):
            continue
        if path.suffix == ".qmlc":
            continue
        if path.name == "qmldir" or path.suffix == ".qmltypes":
            items.append((str(path), str(Path(prefix) / path.relative_to(root).parent)))
            continue
        if path.suffix == ".plugin.json" or path.suffix in {".py", ".json", ".qml", ".js", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".db", ".txt", ".md"}:
            items.append((str(path), str(Path(prefix) / path.relative_to(root).parent)))
    return items


def _is_excluded_qt_path(path: str) -> bool:
    parts = Path(path).parts
    for module in EXCLUDED_QT_MODULES:
        if f"{module}.abi3.so" in parts:
            return True
        if f"{module}.framework" in parts:
            return True
        if module in parts and ("qml" in parts or "lib" in parts):
            return True
        if any(part.startswith(f"lib{module}") for part in parts):
            return True
    return False


def filter_qt_items(items):
    return [item for item in items if not _is_excluded_qt_path(item[0])]


datas = [
    *tree_data(ROOT / "src" / "app", "src/app"),
    *tree_data(ROOT / "src" / "features", "src/features"),
    *collect_data_files("qtawesome"),
]

hiddenimports = [
    *collect_submodules("app"),
    *collect_submodules("features"),
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickControls2",
    "PySide6.QtWidgets",
]

excluded_modules = [
    *(f"PySide6.{module}" for module in sorted(EXCLUDED_QT_MODULES)),
    "IPython",
    "matplotlib",
    "numpy.testing",
    "setuptools",
    "test",
    "tests",
    "tkinter",
    "unittest",
]


a = Analysis(
    [str(ROOT / "tools" / "pyinstaller" / "bootstrap.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    noarchive=False,
    optimize=0,
)
a.binaries = filter_qt_items(a.binaries)
a.datas = filter_qt_items(a.datas)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_exe_icon(),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)

app = BUNDLE(
    coll,
    name=f"{APP_NAME}.app",
    icon=_bundle_icon(),
    bundle_identifier=APP_BUNDLE_ID,
    info_plist={
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": "Py Desktop Tools",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "LSMinimumSystemVersion": "11.0",
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
        "NSHumanReadableCopyright": "Copyright 2026",
    },
)
