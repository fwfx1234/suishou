# AGENTS.md
# 始终使用中文交互
#系统是windows终端环境使用powershell

PySide6 + QML desktop toolbox with a uTools-like launcher (Alt+Space).

## Commands

```bash
uv run app          # run the app
uv sync             # sync dependencies
uv add <pkg>        # add a dependency
```

No lint/typecheck/test commands configured. Hot-reload QML: set `PY_DESKTOP_QML_HOT_RELOAD=1`.

## Architecture

```
src/
  app/           # kernel: main, launcher, commands, plugins, qt adapters, tray, theme
  features/      # plugin modules (api_test, json_parser, qr, clipboard, etc.)
```

Each feature is a plugin package with one manifest. Most packages use `plugin.json`; small shared-runtime packages may use one or more `*.plugin.json` files. The kernel discovers them via `src/app/plugins/manifest_loader.py` which scans subdirectories of `src/features/` for both patterns.

**Entry point**: `src/app/main.py:main()`

**MVVM layering per feature**:
- `plugin.json` or `*.plugin.json` — declares commands, launch mode, entrypoint, QML page, context property
- `runtime.py` — factory for `SimpleQmlRuntime` that creates the ViewModel
- `view_model.py` — `QObject` subclass exposing `Signal`/`Slot`/`Property` for QML binding
- `service.py` — pure Python, no QML dependency
- `*.qml` — View, imports `app/ui`, `app/theme`, and feature-local `components/`

**QML global context properties** (injected in `main.py`):
- `app` → `AppViewModel`
- `launcherBridge` → `LauncherBridge`
- Plugin ViewModels (e.g. `apiTestVm`) are injected only while a plugin session is active

## Plugin system

- **Manifest**: `plugin.json` or `*.plugin.json` in feature directory. `entrypoint: "runtime:create_runtime"` → module `runtime.py`, function `create_runtime`. `qmlPage` resolves relative to `package_dir`.
- **Runtime loading**: `PluginManager._load_runtime()` — lazy, entrypoint parsed as `module:factory`, module imported via `importlib`. Creates synthetic packages so feature-local relative imports work.
- **Session lifecycle**: `PluginSessionManager.open_plugin()` → creates session, injects ViewModel into QML context via `contextProperty`, returns session. On close, sets context property to `None`.
- **Launch modes**: `window` (standalone window), `list` (inline list in launcher), `inline_view` (inline QML in launcher), `none` (execute and hide).
- **Background plugins** (`"activation": "background"`): runtime is never closed by `close_runtime()`.
- **Plugin IDs use hyphens** (e.g. `api-test`), not underscores.
- **Naming**: Python packages/directories use snake_case (e.g. `api_test`); plugin IDs use kebab-case (e.g. `api-test`); QML component files use PascalCase (e.g. `ApiTestPage.qml`).

## Key conventions

- **No comments** should be added to code unless explicitly requested.
- Python 3.13, package manager is `uv`, virtual env in `.venv`.
- `pyproject.toml` sets `where = ["src"]` for setuptools package discovery.
- Startup data: `data/` directory contains SQLite databases (e.g. `api_test.db`). Override with `PY_DESKTOP_TOOLS_DATA_DIR`.
- QML files import shared components via `import "../../app/ui"`, `import "../../app/theme"`.
- Cross-platform SDK-style capabilities belong under `src/app/platform/`. Plugins own their own ViewModel/UI-thread callback handling; do not add a generic Qt adapter layer just to wrap Qt.
- `src/app/platform/` owns platform service assembly and OS-specific implementations under `windows/`, `macos/`, `noop/`, and `common/`. Do not add old flat modules.
- `_plugin_window_config()`: `width`/`height` < 1.0 = ratio of screen, >= 1 = absolute pixels.
- `window_options.multiInstance: true` allows multiple windows of the same plugin.
