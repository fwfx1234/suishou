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
    property string menuResult: ""

    ColumnLayout {
        id: col; width: parent.width - 24; x: 12; y: 12; spacing: 20

        Label { text: "ToolTip / Menu"; font.pixelSize: 20; font.bold: true; color: root.primary }
        Label { text: "悬停提示 + 右键菜单 —— 辅助交互的核心组件"; font.pixelSize: 13; color: Theme.token("color-text-secondary", root.dark) }

        // ToolTip
        ColumnLayout { id: menuSection; spacing: 8
            Label { text: "ToolTip 悬停提示"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", root.dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 48; radius: 8; color: Theme.token("color-bg-subtle", root.dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: Theme.fontFamily.mono; color: Theme.token("color-text-primary", root.dark)
                    text: "Button {\n    ToolTip.visible: hovered\n    ToolTip.text: '点击发送请求'\n    ToolTip.delay: 500  // 延迟 500ms 显示\n}" }
            }
            RowLayout { spacing: 16
                Rectangle { Layout.preferredWidth: 100; Layout.preferredHeight: 36; radius: 8; color: root.primary
                    Label { anchors.centerIn: parent; text: "悬停我"; color: "white"; font.pixelSize: 13 }
                    ToolTip.visible: ttMouse.containsMouse; ToolTip.text: "这是一个 ToolTip 提示"; ToolTip.delay: 300
                    MouseArea { id: ttMouse; anchors.fill: parent; hoverEnabled: true }
                }
                Rectangle { Layout.preferredWidth: 100; Layout.preferredHeight: 36; radius: 8; color: "#F59E0B"
                    Label { anchors.centerIn: parent; text: "也悬停我"; color: "white"; font.pixelSize: 13 }
                    ToolTip.visible: ttMouse2.containsMouse; ToolTip.text: "可以显示多行\n帮助信息"; ToolTip.delay: 200
                    MouseArea { id: ttMouse2; anchors.fill: parent; hoverEnabled: true }
                }
            }
        }

        // Menu
        ColumnLayout { spacing: 8
            Label { text: "Menu 右键菜单"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", root.dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 72; radius: 8; color: Theme.token("color-bg-subtle", root.dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: Theme.fontFamily.mono; color: Theme.token("color-text-primary", root.dark)
                    text: "UiMenuPopup {\n    id: ctxMenu\n    UiMenuItem { text: '复制'; onTriggered: ... }\n    UiMenuSeparator { }\n    UiMenuItem { text: '删除'; destructive: true }\n}\n\n// 在 MouseArea 中\nonClicked: ctxMenu.openAt(this, mouse.x, mouse.y)" }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 80; radius: 8; border.width: 1; border.color: Theme.token("color-border-default", root.dark); color: "transparent"
                Label { anchors.centerIn: parent; text: root.menuResult || "在此区域右键点击"; font.pixelSize: 14; color: Theme.token("color-text-secondary", root.dark) }
                MouseArea { anchors.fill: parent; acceptedButtons: Qt.RightButton; onClicked: function(mouse) { ctxMenu.openAt(this, mouse.x, mouse.y) } }
            }
            UiMenuPopup {
                id: ctxMenu
                implicitWidth: 160
                dark: root.dark
                contentItem: Column {
                    spacing: 0
                    UiMenuItem { width: ctxMenu.width - 8; dark: root.dark; text: "复制"; onTriggered: { root.menuResult = "复制"; ctxMenu.close() } }
                    UiMenuItem { width: ctxMenu.width - 8; dark: root.dark; text: "粘贴"; onTriggered: { root.menuResult = "粘贴"; ctxMenu.close() } }
                    UiMenuSeparator { width: ctxMenu.width - 8; dark: root.dark }
                    UiMenuItem { width: ctxMenu.width - 8; dark: root.dark; text: "删除"; destructive: true; onTriggered: { root.menuResult = "删除"; ctxMenu.close() } }
                }
            }
        }

        Label { text: "ToolTip 用 ToolTip.visible + ToolTip.text + ToolTip.delay 三步。菜单统一用 UiMenuPopup + UiMenuItem + UiMenuSeparator 构建。"; font.pixelSize: 12; color: root.primary; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    }
}
