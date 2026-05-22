# 内存占用与插件释放排查报告（2026-05-22）

## 背景

用户反馈两个症状：(1) 软件整体内存占用过高；(2) 插件退出之后内存没有释放。

本次走查确认 **不是退出路径没被触发，而是释放路径不完整**——独立插件窗口从未被真正销毁，加之 5 分钟的默认保留期，体感"关了也不回收"。本文记录排查结论、改动点与验证数据。

## 根因

### 1. 独立插件窗口永远不释放（主因）

`src/app/plugin_surface_coordinator.py:243` `destroy()` 之前只调用 `win.close()`。
QML `Window` 默认 `close()` 等于 `hide()`，整个 QML 场景图、Loader、子组件留在 `QQmlApplicationEngine` 里。每开一种带独立窗口的插件 → 永久占用一份页面树；反复开关 → 持续累积。

### 2. `force_close_plugin` 不通知销毁窗口

`src/app/launcher_runtime_coordinator.py:341` 之前只 `unload_plugin`，QML 主动 `bridge.closePlugin()` 时窗口表面没被销毁。

### 3. 保留期默认 5 分钟，放大体感

`src/app/plugins/session_manager.py:38` 之前 `300_000ms`。期间 ViewModel + service + ThreadPool 都驻留。

### 4. `ClipboardService.close()` 未清空 listener 列表

`src/app/services/clipboard/service.py:222` 之前 `close()` 不动 `_history_listeners` / `_config_listeners`，Python 闭包会把 ViewModel 拖住。

### 次要观察（未在本次修改范围）

- 后台插件（`clipboard`、`quick-launch`）按设计常驻；`plugin_manager.close_runtime` 跳过 `activation=background`，只能在 `BackgroundManager.stop_all` 时收。
- `StorageManager.database()` 每次 new 一个 `SQLiteDatabase` 壳；底层 connection 走 with 自闭，泄漏风险低，但每次开 plugin 仍会重新建连接。
- `packet_capture` 持有独立 `asyncio` event loop 线程；用户用过该插件后线程会一直在。

## 改动清单

修改：
- `src/app/plugin_surface_coordinator.py` — `destroy` / `destroy_all` 抽出 `_force_destroy_window`，串入 `deleteLater()`；打 `plugin.window.destroyed` 日志。
- `src/app/launcher_runtime_coordinator.py` — `force_close_plugin` 先 `surface.destroy` 再 `session.unload`。
- `src/app/plugins/session_manager.py` — `_retention_interval_ms` 默认 `300_000 → 60_000`；`open/unload/retention_expired` 三处日志补 `sessionsCount`。
- `src/app/services/clipboard/service.py` — `close()` 清空 listener 列表。
- `src/app/app_context.py` — 启动时按 env 装内存探针；shutdown 前打一次最终快照。

新增：
- `src/app/diagnostics/__init__.py`
- `src/app/diagnostics/memory.py` — `snapshot()` / `MemoryProbe` / `install_periodic_snapshot()`，RSS 用 stdlib `resource.getrusage`，按平台换算单位；Windows 走 `ctypes` 调 `GetProcessMemoryInfo`，失败回退 `-1`。
- `tests/test_session_manager.py` — 3 个用例覆盖 `unload_plugin` / `_handle_retention_timeout`。
- `tests/test_core_architecture.py` 末尾追加：
  - `PluginSurfaceCoordinatorTests.test_destroy_calls_delete_later_and_resets_retain`
  - `PluginSurfaceCoordinatorTests.test_destroy_all_clears_window_map_and_deletes_each`
  - `ClipboardServiceTests.test_close_clears_listeners`

## 运行期开关

```bash
# 周期采样，单位 ms；<=0 关闭
SUISHOU_MEM_SNAPSHOT_MS=5000

# 启用 QObject 类型 top-10 统计（成本较高，按需开）
SUISHOU_MEM_QOBJECT_STATS=1

# 调试用：缩短插件会话保留期
SUISHOU_PLUGIN_RETENTION_MS=2000

# 输出到控制台
SUISHOU_LOG_LEVEL=DEBUG
SUISHOU_LOG_CONSOLE=1
```

均可写入 `settings.json`，键分别为 `diagnostics.memorySnapshotMs` / `diagnostics.memoryQObjectStats` / `plugins.retentionMs` / `logging.level` / `logging.console`。

## 验证

### 单元测试

```bash
uv run pytest --ignore=tests/platform_layer -q
# → 429 passed, 2 skipped, 0 failed
```

`tests/platform_layer/*` 在 macOS 上收集失败（依赖 Windows-only `ctypes.windll`），与本次改动无关。

### 启动基线（已自动采集）

```bash
SUISHOU_MEM_SNAPSHOT_MS=2000 SUISHOU_LOG_LEVEL=DEBUG \
SUISHOU_LOG_CONSOLE=1 uv run app
```

启动 ~7s 内的 `app.memory.periodic`：

| t(s) | rssMb | gcObjects | sessions | windows |
|------|-------|-----------|----------|---------|
| 2    | 222.25 | 91,940    | 0        | 0       |
| 4    | 223.08 | 91,956    | 0        | 0       |
| 6    | 223.08 | 91,956    | 0        | 0       |

结论：空闲基线 ~ 223 MB，gc 对象稳定，启动期间无泄漏迹象。后台插件（quick-launch, clipboard）已自动启动并常驻。

### 待人工验证的"开关 10 次"用例

```bash
SUISHOU_MEM_SNAPSHOT_MS=5000 SUISHOU_LOG_LEVEL=DEBUG \
SUISHOU_LOG_CONSOLE=1 SUISHOU_PLUGIN_RETENTION_MS=2000 uv run app \
  2>&1 | tee /tmp/mem_audit.log
```

操作脚本（请人工执行）：
1. 启动后等 30s，记录基线一行。
2. Alt+Space → 输入 `api` → 进入 api-test → 关窗 → 等 5s（让 retention 过期）→ 记录一行。
3. 重复步骤 2 共 10 次，记录每轮关窗 5s 后的快照。
4. 切换 `clipboard`、`json-parser`、`remote-files` 各开/关一次，每次后记录。
5. 退出应用，对比 `app.memory.shutdown` 与启动基线。

预期数据点（修复后）：
- 每轮 `windows` 应在 retention 过期后归零（`plugin.window.destroyed` 日志带 `windowsCount=0`）。
- `rssMb` 在 10 轮后稳定波动，**不再单调上涨**。
- `gcObjects` 在 gc 触发后会回落，10 轮峰值不应翻倍。

可粘到下面表格里：

| 轮次 | 操作 | rssMb | gcObjects | sessions | windows |
|------|------|-------|-----------|----------|---------|
| 基线 | 启动后 30s |  |  | 0 | 0 |
| 1 | api-test 开/关 |  |  |  |  |
| 2 | … |  |  |  |  |
| 10 | … |  |  |  |  |
| 切换 | clipboard |  |  |  |  |
| 切换 | json-parser |  |  |  |  |
| 切换 | remote-files |  |  |  |  |
| 退出 | app.memory.shutdown |  |  | 0 | 0 |

### 修复前对照（可选）

`git stash` 暂存改动 → 跑同样脚本 → 对比 `rssMb` 与 `windows` 字段：修复前应出现 `windows>0` 且 RSS 随轮次单调上涨。

## 不在本次范围

- 不引入 `psutil` / `memory-profiler` 运行期依赖。
- 不重构 `Window` 复用语义（`_adopt_existing_window_surface`）。
- 不改 background 插件常驻策略。
- 不动 `QmlPluginSession._view_model.deleteLater()` 的时序——QML 端只要 Window 真销毁，binding 会随之断开。
