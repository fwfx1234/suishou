# 公共 UI 组件库

`src/app/ui` 是插件共享组件库。新插件页面优先导入：

```qml
import "../../app/ui"
import "../../app/theme"
```

如果插件目录层级不同，按相对路径调整到 `src/app/ui` 和 `src/app/theme`。

## 设计定位

- 现代工具型桌面界面，适配 macOS 视觉习惯。
- 默认使用 mac 蓝作为强调色。
- 控件高度以 28-32px 为主，适合紧凑桌面密度。
- 深浅色模式通过 `dark` 属性统一切换。
- 基础控件内置 hover、pressed、focus、disabled、selected、danger 等状态。

## 组件选择

| 场景 | 使用组件 |
|------|----------|
| 普通操作按钮 | `UiButton` |
| 仅图标按钮 | `UiIconButton` |
| 工具栏图标按钮 | `UiToolbarButton` |
| 单行输入 | `UiTextField` |
| 多行表单输入 | `UiTextArea` |
| 轻量文本编辑/预览 | `UiTextEdit` |
| 下拉选择 | `UiComboBox` |
| 自定义弹窗面板 | `UiPopup` |
| 菜单/右键菜单 | `UiMenuPopup` + `UiMenuItem` |
| 确认弹窗 | `UiConfirmPopup` |
| 轻提示 | `UiToast` |
| 卡片容器 | `UiCard` |
| 面板容器 | `UiPanel` |
| 表单行 | `UiFormRow` |
| 分割线 | `UiDivider` |
| 状态标签 | `UiBadge` |
| 可点击标签 | `UiChip` |
| 空状态 | `UiEmptyState` |
| 列表行 | `UiListRow` |

## 迁移规则

业务 QML 不直接使用裸 `Menu`、`Popup`、`ComboBox`、`TextField`、`TextArea`、`TextEdit`、`Button`。这些原生控件只应出现在公共组件内部。

系统原生对话框可以保留，例如 `MessageDialog`、`FileDialog`。复杂业务容器可以保留私有组件，但内部基础输入、按钮、下拉、菜单应使用公共组件。

文本输入相关组件已内置中文右键菜单，插件不需要单独处理剪切、复制、粘贴、全选菜单。

## 常用示例

```qml
UiTextField {
    dark: root.dark
    Layout.fillWidth: true
    placeholderText: "输入名称"
}

UiButton {
    dark: root.dark
    text: "保存"
    iconName: "mdi6.content-save-outline"
    variant: "primary"
}

UiMenuPopup {
    id: menu
    dark: root.dark
    contentItem: Column {
        UiMenuItem { width: menu.width - 8; dark: root.dark; text: "复制" }
        UiMenuSeparator { width: menu.width - 8; dark: root.dark }
        UiMenuItem { width: menu.width - 8; dark: root.dark; text: "删除"; destructive: true }
    }
}
```
