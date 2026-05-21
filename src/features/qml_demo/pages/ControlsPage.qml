pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

Flickable {
    id: root
    anchors.fill: parent; clip: true; contentHeight: col.implicitHeight + 32
    property bool dark: false; property color primary: Theme.token("color-primary-active", dark)

    ColumnLayout {
        id: col; width: parent.width - 24; x: 12; y: 12; spacing: 20

        Label { text: "控件大全"; font.pixelSize: 20; font.bold: true; color: root.primary }
        Label { text: "项目通用 UI 组件（src/app/ui/），所有控件接受 dark 属性自动适配主题"; font.pixelSize: 13; color: Theme.token("color-text-secondary", root.dark) }

        // 每个控件 = 代码 + 实例
        Repeater {
            model: [
                { title: "UiButton", code: 'UiButton {  text: "发送"; iconName: "mdi6.send"; variant: "primary"; dark: root.dark  }', demo: 'button' },
                { title: "UiIconButton", code: 'UiIconButton { iconName: "mdi6.cog-outline"; tooltip: "设置"; dark: root.dark }', demo: 'iconbutton' },
                { title: "UiTextField", code: 'UiTextField {  dark: root.dark;  placeholderText: "输入...";  text: vm.prop  }', demo: 'textfield' },
                { title: "UiTextArea", code: 'UiTextArea {  dark: root.dark;  readOnly: false;  Layout.fillWidth: true  }', demo: 'textarea' },
                { title: "UiTextEdit", code: 'UiTextEdit { dark: root.dark; framed: true; text: "可选中文本" }', demo: 'textedit' },
                { title: "UiSwitch", code: 'UiSwitch {  dark: root.dark;  checked: vm.boolProp;  onToggled: { }  }', demo: 'switch' },
                { title: "UiCheckBox", code: 'UiCheckBox {  dark: root.dark;  checked: vm.boolProp  }', demo: 'checkbox' },
                { title: "UiComboBox", code: 'UiComboBox {  dark: root.dark;  model: [{text:"A",value:"a"}];  textRole: "text"  }', demo: 'combobox' },
                { title: "UiCard / UiBadge / UiChip", code: 'UiCard { UiBadge { text: "GET" }; UiChip { text: "启用" } }', demo: 'display' },
                { title: "UiPopup / UiMenuPopup", code: 'UiPopup { ... }  UiMenuPopup { UiMenuItem { text: "复制" } }', demo: 'popup' },
            ]
            delegate: ColumnLayout {
                id: controlExample
                required property var modelData
                spacing: 6
                Label { text: controlExample.modelData.title; font.pixelSize: 14; font.bold: true; color: Theme.token("color-text-primary", root.dark) }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 34; radius: 6; color: Theme.token("color-bg-subtle", root.dark)
                    Label { anchors.verticalCenter: parent.verticalCenter; x: 10; font.pixelSize: 11; font.family: Theme.fontFamily.mono; color: Theme.token("color-text-primary", root.dark); text: controlExample.modelData.code }
                }
            }
        }

        // 活例
        Label { text: "活例"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", root.dark) }
        RowLayout { spacing: 12
            UiButton { text: "主要按钮"; iconName: "mdi6.check"; dark: dark; variant: "primary" }
            UiButton { text: "次要按钮"; dark: dark; variant: "secondary" }
            UiButton { text: "危险操作"; dark: dark; variant: "secondary"; danger: true }
            UiIconButton { dark: dark; iconName: "mdi6.cog-outline"; tooltip: "设置" }
            UiSwitch { dark: dark; checked: true }
            UiCheckBox { dark: dark; checked: true }
        }
        UiTextField { dark: dark; Layout.fillWidth: true; placeholderText: "输入框示例..." }
        UiTextArea { dark: dark; Layout.fillWidth: true; Layout.preferredHeight: 72; placeholderText: "多行文本，右键会显示统一中文菜单" }
        UiComboBox { dark: dark; Layout.preferredWidth: 180; model: [{text:"选项 A",value:"a"},{text:"选项 B",value:"b"},{text:"选项 C",value:"c"}]; textRole: "text"; valueRole: "value" }
        UiCard {
            dark: dark
            Layout.fillWidth: true
            Layout.preferredHeight: 74
            RowLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 10
                UiBadge { text: "macOS"; badgeColor: Theme.token("color-primary-bg", dark); textColor: Theme.token("color-primary-active", dark) }
                UiChip { dark: dark; text: "紧凑"; selected: true }
                Label { Layout.fillWidth: true; text: "卡片、标签和胶囊用于插件列表、状态和表单摘要"; color: Theme.token("color-text-regular", root.dark); elide: Text.ElideRight }
            }
        }
        UiEmptyState {
            dark: dark
            Layout.alignment: Qt.AlignHCenter
            iconName: "mdi6.package-variant"
            title: "暂无内容"
            message: "插件页面可以直接复用空状态组件。"
        }

        Label { text: "所有控件位于 src/app/ui/。新插件页面优先使用这些通用组件，保证主题和风格一致。"; font.pixelSize: 12; color: root.primary; wrapMode: Text.Wrap; Layout.fillWidth: true }
    }
}
