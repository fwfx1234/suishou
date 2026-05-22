# Suishou 架构复杂度收敛调整文档

本文基于当前代码状态，对项目中已经出现的过度设计、职责边界不清和阶段性兼容层进行整理，给出可分阶段执行的调整方案。

本文不是推翻当前架构。当前插件模型、命令系统、MVVM 分层、会话保留和平台能力方向整体成立；需要处理的是抽象层已经长出来，但边界还没有收紧，导致核心路径阅读和维护成本偏高。

## 1. 调整目标

### 1.1 目标

- 降低启动主流程的认知负担，让应用组装、运行期事件和退出清理各有明确入口。
- 让平台能力只初始化一次，避免创建后又被覆盖的隐式对象。
- 收敛平台层公共 import 路径，减少新旧目录结构并存造成的歧义。
- 明确插件 Session、Surface、Launcher Bridge 的职责边界，减少状态分散。
- 把后台插件线程能力从“看似通用”调整为“受约束且可解释”。
- 让插件服务注册表既保留扩展性，又减少核心服务全靠字符串 key 的运行期风险。

### 1.2 非目标

- 不重写插件系统。
- 不移除插件会话保留机制。
- 不大规模重构所有 feature 插件。
- 不引入新的大型依赖、IoC 容器或框架式事件总线。
- 不在本轮解决 macOS 所有平台适配细节。

## 2. 总体判断

当前项目不是典型的“完全过度设计”，而是一次架构升级处在中间态：

- Manifest 驱动插件、懒加载 Runtime、MVVM、平台 API 外观这些方向是合理的。
- 命令搜索拆成排序、上下文匹配、应用索引、使用频率等模块也基本合理。
- 问题集中在运行期组装、平台服务注入、兼容 re-export、插件生命周期状态和后台线程能力几个地方。

因此本次调整策略应该是“收敛和定界”，不是“推倒重来”。

## 3. 当前主要问题

### 3.1 ApplicationRuntime 仍然是总控脚本

现状：

- `src/app/main.py` 已经保持薄入口。
- `src/app/app_runtime.py` 接管了实际运行期。
- 但 `ApplicationRuntime.run()` 仍同时负责：
  - QML engine 初始化。
  - 全局 context property 注入。
  - 平台服务、存储、命令索引、动态命令注册表组装。
  - Manifest 加载和插件管理器创建。
  - 后台插件启动。
  - 热键注册和热键配置刷新。
  - Launcher 窗口定位。
  - 插件打开、挂起、脱离到窗口、列表模式交互。
  - 重启、托盘、退出清理。

影响：

- 新增插件生命周期行为时，很容易继续往 `run()` 里塞闭包。
- 信号连接散落在一个长方法中，阅读时必须同时理解多个子系统。
- 测试和回归很难聚焦到单一职责。

调整方向：

- `ApplicationRuntime.run()` 只保留“创建应用上下文、启动运行期、进入 Qt event loop”。
- 把启动组装拆成 `ApplicationBootstrapper` 或私有方法组。
- 把运行期信号连接拆到专门 coordinator。
- 把退出清理聚合成一个 runtime context 的 `shutdown()`。

推荐拆分：

```text
src/app/app_runtime.py
  ApplicationRuntime
    run()

src/app/app_bootstrap.py
  ApplicationBootstrapper
    build() -> ApplicationContext

src/app/app_context.py
  ApplicationContext
    engine
    qt_app
    app_vm
    platform_services
    storage
    command_index
    plugin_context
    plugin_manager
    session_manager
    background_manager
    command_service
    launcher_bridge
    surface_coordinator
    hotkey_coordinator
    tray_coordinator
    shutdown()

src/app/launcher_runtime_coordinator.py
  LauncherRuntimeCoordinator
    connect()
    on_plugin_launched()
    on_plugin_suspended()
    on_plugin_detached_to_window()
```

是否必须新增这些文件可按实际改动控制，但职责边界应按这个方向收拢。

验收标准：

- `ApplicationRuntime.run()` 控制在约 80 行以内。
- 插件打开链路只在一个 coordinator 中组装，不再散落在 `run()` 闭包里。
- 退出清理只有一个入口，不需要阅读多个局部函数才能确认清理顺序。

### 3.2 平台服务存在重复初始化和覆盖

现状：

- `create_platform_services()` 内部创建 `StorageManager()` 和 `PlatformCommandApiFactory(None)`。
- `ApplicationRuntime.run()` 随后又创建新的 `StorageManager()` 和 `DynamicCommandRegistry()`，并覆盖 `platform_services.storage_factory` 与 `platform_services.dynamic_command_api_factory`。

影响：

- 代码读起来像平台工厂已经完成依赖组装，但实际核心依赖由上层覆盖。
- 后续维护者可能在平台工厂里使用了被覆盖前的 storage，造成隐蔽 bug。
- 对测试不友好，依赖来源不单一。

调整方向：

让平台工厂只接收已经确定的核心依赖，或者只创建平台相关能力，不创建应用级 storage / dynamic registry。

推荐方案 A：

```python
def create_platform_services(
    *,
    storage: StorageManager,
    dynamic_commands: DynamicCommandRegistry,
) -> PlatformServices:
    ...
```

`ApplicationRuntime` 中：

```python
storage = StorageManager()
dynamic_commands = DynamicCommandRegistry()
platform_services = create_platform_services(
    storage=storage,
    dynamic_commands=dynamic_commands,
)
```

推荐方案 B：

```python
def create_platform_services() -> PlatformServices:
    ...
```

但 `PlatformServices` 不包含 `storage_factory` 和 `dynamic_command_api_factory`，由 `PlatformApi` 或 `PluginContext` 另行组合。

倾向选择：

- 短期选方案 A，改动较小。
- 长期如果平台服务和插件 API 继续增长，再考虑方案 B。

验收标准：

- `StorageManager()` 在启动主路径只创建一次。
- `PlatformCommandApiFactory` 初始化时就持有真实 registry，不再先 `None` 后覆盖。
- `create_platform_services()` 中没有会被上层立即替换的对象。

### 3.3 平台层兼容 re-export 过多

现状：

平台层同时存在：

```text
src/app/platform/apps_windows.py
src/app/platform/apps_macos.py
src/app/platform/apps_noop.py
src/app/platform/hotkey_windows.py
src/app/platform/hotkey_macos.py
src/app/platform/hotkey_noop.py
src/app/platform/storage.py
src/app/platform/permissions.py
src/app/platform/dynamic_commands.py
src/app/platform/system_commands.py
src/app/platform/external_launcher.py

src/app/platform/windows/
src/app/platform/macos/
src/app/platform/noop/
src/app/platform/common/
```

旧平铺文件大多只是 compatibility re-export。

影响：

- 新代码不知道应该 import `app.platform.storage` 还是 `app.platform.common.storage`。
- IDE 自动补全会把兼容层也展示出来。
- 文档一旦没有同步，很容易产生两套“看似都对”的路径。

调整方向：

- 明确公共入口只有两类：
  - 插件和业务代码：通过 `ctx.platform` 使用能力，不直接 import 平台实现。
  - 内核代码：从 `app.platform.factory` 和 `app.platform.services` 组装。
- OS 实现只从 `app.platform.windows` / `macos` / `noop` import。
- common 实现只给 factory 和 platform api 内部使用。
- 旧平铺 compatibility 文件保留一个迁移周期，然后删除。

建议迁移步骤：

1. 全仓搜索旧路径 import。
2. 内部代码全部改为新路径。
3. 文档中声明旧路径已废弃。
4. 保留 compatibility 文件，但不再新增引用。
5. 一个稳定版本后删除旧平铺文件。

验收标准：

- `src/` 中不再 import `app.platform.apps_windows`、`app.platform.hotkey_windows`、`app.platform.dynamic_commands` 等旧平铺模块。
- 新插件开发文档只推荐 `ctx.platform`，不鼓励直接 import 平台实现。
- compatibility 文件只剩第三方插件迁移用途，且有明确删除计划。

### 3.4 插件 Session / Surface / Bridge 状态分散

现状：

当前插件打开和关闭涉及三层：

- `PluginSessionManager` 管 Python Session、ViewModel context property、retention timer。
- `PluginSurfaceCoordinator` 管独立窗口、inline/list host、retained close。
- `LauncherBridge` 管 QML 信号、插件输入、列表项、关闭/挂起请求。

这三层都保存或转发了一部分插件状态。

影响：

- “插件当前是 active、retained 还是 unloaded”需要跨文件推理。
- inline/list/window 三种 host 的处理逻辑容易分叉。
- 新增 `multiInstance` 或 session id 时，当前以 `plugin_id` 为 key 的结构会形成阻碍。

调整方向：

明确单一真相：

```text
PluginSessionManager
  只管理 Python Session 生命周期：
  active / retained / unloaded
  context property 注入和释放
  retention timer
  session reuse / reactivate

PluginSurfaceCoordinator
  只管理 UI surface：
  window 创建、显示、隐藏、销毁
  inline/list host 通知
  不判断 session 是否可复用

LauncherBridge
  只作为 QML 边界：
  搜索结果属性
  用户意图信号
  不持有插件生命周期状态
```

建议新增一个轻量请求对象，减少散乱参数：

```python
@dataclass(frozen=True, slots=True)
class PluginLaunchRequest:
    plugin_id: str
    command_id: str = ""
    input_text: str = ""
    payload: dict = field(default_factory=dict)
    preferred_host: PluginHost | None = None
```

打开链路调整为：

```text
LauncherBridge emits PluginLaunchRequest data
  -> LauncherRuntimeCoordinator.open_plugin(request)
  -> PluginSessionManager.open_plugin(request)
  -> PluginSurfaceCoordinator.show(session, request)
```

挂起链路调整为：

```text
LauncherBridge emits suspend intent
  -> LauncherRuntimeCoordinator.suspend_plugin(plugin_id, host)
  -> PluginSurfaceCoordinator.suspend_surface(plugin_id, host)
  -> PluginSessionManager.suspend_plugin(plugin_id, host)
```

保留到期链路调整为：

```text
PluginSessionManager emits/calls retention_expired(plugin_id, state)
  -> LauncherRuntimeCoordinator
  -> PluginSurfaceCoordinator.destroy_or_notify_expired(plugin_id, state.host)
  -> PluginSessionManager.unload_plugin(plugin_id)
```

验收标准：

- `LauncherBridge` 不直接清空或维护插件生命周期状态，只维护 QML 展示必需的搜索结果和列表模型。
- `PluginSurfaceCoordinator.show()` 不负责决定是否创建或复用 Session，只接收已经确定的 Session。
- 插件生命周期关键动作在日志里能看到统一 trace：launch -> session active -> surface shown -> suspend/unload。

### 3.5 后台插件线程能力开放过早

现状：

- Manifest 支持 `threadedBackground`。
- 实际 `BackgroundManager` 又用 `_THREAD_SAFE_PLUGIN_IDS = {"clipboard"}` 白名单限制。
- 线程上下文会剔除 `platform` 服务，避免 Qt 对象跨线程。

影响：

- 对插件作者来说，字段看起来是通用能力，实际只有特例可用。
- 后续插件误开 `threadedBackground` 时，只能运行期回退并打 warning。
- 线程上下文和主线程上下文服务合并逻辑增加了复杂度。

调整方向有两种：

方案 A：先收回通用线程能力。

- 移除或废弃 manifest 中的 `threadedBackground`。
- 剪贴板后台如果需要线程，放在剪贴板插件内部自己管理。
- `BackgroundManager` 只负责主线程启动 background runtime。

方案 B：把线程能力正式产品化。

- Manifest 明确声明 `threadModel`: `"main"` / `"worker"`。
- 文档列出 worker 可用服务：storage、纯 Python registry、非 Qt service。
- 需要提供线程安全插件上下文类型。
- 背景服务注册回主线程时必须走明确的注册队列或 signal，不直接 merge dict。

倾向选择：

- 当前项目规模下建议选方案 A。
- 等至少出现第二个真实线程安全后台插件，再升级到方案 B。

验收标准：

- 插件开发文档不再让作者误以为后台线程是普遍可用能力。
- `BackgroundManager` 不再维护线程白名单和服务剔除/合并逻辑，除非明确选择方案 B。
- 剪贴板后台行为保持不变。

### 3.6 ServiceRegistry 类型边界偏弱

现状：

`ServiceRegistry` 同时是：

- `MutableMapping[str, object]`
- 带 `platform` / `storage` / `clipboard` property 的轻量 typed facade

影响：

- 核心服务 key 仍然是字符串。
- 插件之间共享服务很方便，但运行期错误更容易延后暴露。
- 后台线程剔除服务时依赖字符串 key，难以靠类型检查发现问题。

调整方向：

保留扩展能力，但核心服务显式化：

```python
@dataclass
class CoreServices:
    platform: PlatformApi | None = None
    storage: StorageManager | None = None
    clipboard: object | None = None
    extra: dict[str, object] = field(default_factory=dict)
```

或保留现有 `ServiceRegistry`，但增加明确方法：

```python
def require_platform(self) -> PlatformApi: ...
def require_storage(self) -> StorageManager: ...
def get_service(self, key: str, expected_type: type[T]) -> T | None: ...
def set_service(self, key: str, value: object) -> None: ...
```

短期建议：

- 先不替换整个 registry。
- 给核心服务增加 `require_*` 方法。
- 插件开发文档推荐 `ctx.platform` 优先，`ctx.services` 只用于插件间共享服务。

验收标准：

- 核心代码不再大量直接访问 `services["platform"]` 字符串。
- 插件读取共享服务时能有一个标准 fallback 写法。
- 测试覆盖 `require_*` 的成功和失败路径。

## 4. 分阶段执行计划

### 阶段 0：基线保护

目的：

在调整前确认当前行为，避免架构清理引入隐形回归。

建议动作：

1. 保留当前工作区修改，不做破坏性 reset。
2. 运行基础验证：

```powershell
uv run python -m compileall src
scripts\smoke_import.ps1
scripts\smoke_plugin_manifests.ps1
scripts\smoke_storage.ps1
scripts\smoke_tests.ps1
```

3. 手动验证：
   - `uv run app`
   - `Alt+Space` 打开启动器
   - 搜索并打开 `json-parser`
   - 打开/关闭/重新打开 `api-test`
   - 打开剪贴板历史
   - 启动一个系统应用

产出：

- 一份当前可运行行为记录。
- 如果已有失败，先记录为已知问题，不和架构调整混在一起。

### 阶段 1：收敛平台服务注入

优先级：高。

原因：

这是收益高、风险相对低的问题。修掉后，核心依赖来源会清晰很多。

建议改动：

- 修改 `create_platform_services()` 签名，让 `storage` 和 `dynamic_commands` 从外部传入。
- 删除工厂内部临时 `StorageManager()`。
- 删除 `PlatformCommandApiFactory(None)` 后再覆盖的路径。
- 更新调用点。

风险：

- 平台工厂测试或导入脚本可能依赖无参调用。

缓解：

- 可以先提供默认参数保持兼容：

```python
def create_platform_services(
    *,
    storage: StorageManager | None = None,
    dynamic_commands: DynamicCommandRegistry | None = None,
) -> PlatformServices:
    storage = storage or StorageManager()
    dynamic_commands = dynamic_commands or DynamicCommandRegistry()
```

但启动主路径必须显式传入，避免再次出现覆盖。

验收：

- 搜索 `StorageManager()`，确认启动主路径只有一个应用级实例。
- smoke 脚本通过。

### 阶段 2：拆分 ApplicationRuntime.run()

优先级：高。

原因：

这是后续所有生命周期调整的地基。

建议改动：

1. 先抽私有方法，不急着新增多个文件：

```python
def _create_engine(self) -> QQmlApplicationEngine: ...
def _build_kernel_services(self) -> KernelServices: ...
def _load_main_window(self, engine) -> object | None: ...
def _connect_runtime_signals(self, context) -> None: ...
def _start_background_services(self, context) -> None: ...
def _install_shutdown(self, context) -> None: ...
```

2. 第二步再把稳定结构移入新文件：

```text
app_bootstrap.py
launcher_runtime_coordinator.py
```

3. 把局部闭包提升为 coordinator 方法：
   - `on_plugin_launched`
   - `on_plugin_suspended`
   - `on_plugin_detached_to_window`
   - `on_plugin_force_closed`
   - `on_plugin_input_edited`
   - `on_plugin_list_item_activated`
   - `on_plugin_list_item_action`

风险：

- Qt signal 连接对对象生命周期敏感，coordinator 必须被强引用保存。

缓解：

- 将 coordinator 存在 `ApplicationContext` 或 `qt_app.setProperty()` 中。
- 每拆一组信号就运行应用手测。

验收：

- `ApplicationRuntime.run()` 只保留高层流程。
- 所有信号连接集中在一个方法或一个 coordinator。
- 应用退出时清理顺序清晰且只有一个入口。

### 阶段 3：明确插件生命周期职责

优先级：高。

原因：

插件 session 保留是当前架构最复杂的核心行为，必须让状态来源更清楚。

建议改动：

- 新增 `PluginLaunchRequest`。
- `LauncherBridge` 只负责把 QML 输入转成启动请求数据。
- `LauncherRuntimeCoordinator` 负责 request -> session -> surface。
- `PluginSessionManager` 不直接关心 QML host 细节，只记录 `PluginHost`。
- `PluginSurfaceCoordinator` 不决定 session reuse，只按 session state 显示或销毁 UI。

需要特别注意：

- `list` 模式的列表数据现在由 `bridge.setPluginListItems()` 维护，调整时不要让 list 模式断掉。
- inline host 的 `retainInlineHost(plugin_id)` 和 retained expired 通知仍需保留。
- window close 时的 `retainedCloseRequested` 仍应先 suspend，而不是 unload。

验收：

- `inline_view` 插件关闭后能在保留期内恢复。
- `window` 插件关闭后能在保留期内恢复。
- `list` 插件输入过滤仍然正常。
- 保留到期后 context property 被清空，ViewModel `dispose()` 被调用。

### 阶段 4：平台 import 路径收敛

优先级：中。

原因：

它不一定马上导致 bug，但会持续增加维护噪音。

建议改动：

- 全仓替换内部旧路径 import。
- 将旧平铺模块标记为 deprecated compatibility。
- 在设计文档中写清楚：
  - 插件只能用 `ctx.platform`。
  - 内核平台实现只从 `app.platform.windows` / `macos` / `noop` / `common` 引入。
  - `app.platform.__init__` 只导出稳定模型和公共 facade。

可删除候选：

```text
src/app/platform/apps_windows.py
src/app/platform/apps_macos.py
src/app/platform/apps_noop.py
src/app/platform/hotkey_windows.py
src/app/platform/hotkey_macos.py
src/app/platform/hotkey_noop.py
src/app/platform/storage.py
src/app/platform/permissions.py
src/app/platform/dynamic_commands.py
src/app/platform/system_commands.py
src/app/platform/external_launcher.py
```

是否立即删除取决于是否需要兼容外部插件。若外部插件尚未正式开放，可以直接删；如果已经有个人插件在用，保留一个版本周期。

验收：

- `rg "app\\.platform\\.(apps_|hotkey_|dynamic_commands|storage|permissions|external_launcher|system_commands)" src tests` 不再命中内部使用。
- 文档只出现推荐路径，不再把旧路径当作正常入口。

### 阶段 5：后台插件线程能力降级或正式化

优先级：中。

建议默认选择降级：

- manifest 中 `threadedBackground` 标记为 internal/deprecated。
- `BackgroundManager` 主流程只负责 background runtime 的 start/stop。
- 剪贴板服务内部自己决定是否使用后台任务。

如果选择正式化，则必须同步补齐：

- worker 线程上下文类型。
- 可用服务白名单。
- 服务注册回主线程的机制。
- 插件开发文档中的线程安全 contract。
- 至少两个真实 worker background 插件验证。

验收：

- 后台插件文档不再给出过度承诺。
- `BackgroundManager` 中没有“字段通用但只有白名单可用”的矛盾设计。

### 阶段 6：ServiceRegistry 收口

优先级：中低。

原因：

当前 registry 虽弱类型，但还没有变成最急迫风险。适合在生命周期和平台服务稳定后处理。

建议改动：

- 增加 `require_platform()`、`require_storage()`、`get_typed()`。
- 核心代码从直接字符串访问迁移到方法或 property。
- 插件共享服务继续允许字符串 key，但要求 key 写成常量。

示例：

```python
CLIPBOARD_SERVICE_KEY = "clipboard.background"
```

验收：

- 核心服务读取路径清晰。
- 测试覆盖缺失服务时报错信息。
- 插件开发文档推荐 `ctx.platform` 和明确 service key 常量。

## 5. 推荐最终模块边界

调整后理想边界：

```text
app.main
  只做日志、QApplication、字体、ApplicationRuntime.run()

app.app_runtime
  只做高层运行流程

app.app_bootstrap
  创建 engine、services、managers、bridge、coordinators

app.launcher_runtime_coordinator
  连接 LauncherBridge 与 PluginSessionManager / PluginSurfaceCoordinator

app.plugins.session_manager
  管 Python Session、context property、retention、reactivate

app.plugin_surface_coordinator
  管 QML surface：window / inline_view / list

app.launcher.launcher_bridge
  QML 边界：搜索、结果、用户意图信号

app.platform.factory
  根据 OS 选择平台实现，接收应用级依赖，不偷偷创建核心依赖
```

## 6. 风险清单

### 6.1 Qt 对象生命周期

风险：

- coordinator 被局部变量释放，signal 连接失效。
- QML window 已删除后 Python 继续访问导致 RuntimeError。

应对：

- coordinator 挂在 `ApplicationContext`。
- 保留 `is_qobject_alive()` 检查。
- 改动 surface 逻辑后重点手测窗口关闭和保留到期。

### 6.2 插件 context property 清理

风险：

- Session 卸载后 QML 仍引用旧 ViewModel。
- context property 没清空导致旧对象被保留。

应对：

- `PluginSessionManager.unload_plugin()` 仍是唯一清理入口。
- 增加测试：打开插件 -> unload -> context property 为 None。

### 6.3 list 模式回归

风险：

- list 模式不像 inline/window 有 QML 页面，容易在 coordinator 拆分时漏掉 `pluginListItems` 更新。

应对：

- 给 `app-launcher` 写一个最小集成测试或 smoke 手测步骤。
- 保留 `bridge.setPluginListItems()`，但由 coordinator 统一调用。

### 6.4 后台剪贴板服务

风险：

- 剪贴板服务同时影响上下文推荐、热键配置、剪贴板历史 UI。

应对：

- 后台插件阶段单独回归剪贴板：
  - 启动后能捕获最新文本。
  - `Alt+V` 能打开历史。
  - 设置中的热键变更能刷新注册。

## 7. 测试与验证策略

每个阶段至少运行：

```powershell
uv run python -m compileall src
scripts\smoke_import.ps1
scripts\smoke_plugin_manifests.ps1
scripts\smoke_tests.ps1
```

涉及存储或剪贴板时增加：

```powershell
scripts\smoke_storage.ps1
```

涉及 UI 生命周期时手动验证：

```powershell
uv run app
```

手动验证清单：

- `Alt+Space` 显示/隐藏启动器。
- 搜索插件命令，结果排序正常。
- 打开 `json-parser`，输入内容，关闭后重新打开。
- 打开 `api-test` 独立窗口，关闭后保留期内恢复。
- 打开 `app-launcher` list 模式，输入过滤、选择项。
- 打开剪贴板历史，确认后台服务存在。
- 启动系统应用或系统动作。
- 退出应用，确认无明显异常日志。

## 8. 建议执行顺序摘要

推荐顺序：

1. 平台服务注入收敛。
2. `ApplicationRuntime.run()` 拆分。
3. 插件生命周期 coordinator 化。
4. 平台 import 路径收敛。
5. 后台线程能力降级或正式化。
6. `ServiceRegistry` 类型边界收口。

不建议一口气全部改完。每个阶段都应该能独立运行、独立验证、独立回退。

## 9. 完成后的文档更新

当调整完成后，应把长期结论沉淀到：

- `docs/project-design.zh-CN.md`
- `docs/plugin-development.zh-CN.md`

本文作为阶段性调整文档，可以在所有阶段完成后删除，避免长期文档和计划文档互相漂移。

