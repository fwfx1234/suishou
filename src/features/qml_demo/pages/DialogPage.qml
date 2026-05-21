pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../../app/ui"
import "../../../app/theme"

Flickable {
    id: root
    anchors.fill: parent; clip: true; contentHeight: col.implicitHeight + 32
    property bool dark: false; property color primary: "#8B5CF6"
    property string dialogResult: ""; property string filePath: ""

    ColumnLayout {
        id: col; width: parent.width - 24; x: 12; y: 12; spacing: 20

        Label { text: "弹窗与对话框"; font.pixelSize: 20; font.bold: true; color: root.primary }
        Label { text: "MessageDialog / FileDialog / UiPopup —— 消息、文件选择和统一自定义弹窗"; font.pixelSize: 13; color: Theme.token("color-text-secondary", root.dark) }

        // MessageDialog
        ColumnLayout { spacing: 8
            Label { text: "MessageDialog 消息弹窗"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", root.dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 38; radius: 8; color: Theme.token("color-bg-subtle", root.dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: Theme.fontFamily.mono; color: Theme.token("color-text-primary", root.dark)
                    text: 'MessageDialog { title: "提示"; text: "消息内容"; buttons: MessageDialog.Ok }' }
            }
            RowLayout { spacing: 8; UiButton { text: "显示消息"; dark: root.dark; variant: "primary"; onClicked: msgDialog.open() } Label { text: root.dialogResult; font.pixelSize: 12; color: Theme.token("color-text-secondary", root.dark) } }
        }

        // FileDialog
        ColumnLayout { spacing: 8
            Label { text: "FileDialog 文件选择"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", root.dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 38; radius: 8; color: Theme.token("color-bg-subtle", root.dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: Theme.fontFamily.mono; color: Theme.token("color-text-primary", root.dark)
                    text: 'FileDialog { fileMode: FileDialog.OpenFile; title: "选择文件" }' }
            }
            RowLayout { spacing: 8; UiButton { text: "选择文件..."; dark: root.dark; variant: "secondary"; onClicked: filePickDialog.open() } Label { text: root.filePath; font.pixelSize: 12; color: root.primary; Layout.fillWidth: true; elide: Text.ElideMiddle } }
        }

        // Popup
        ColumnLayout { spacing: 8
            Label { text: "UiPopup 自定义面板"; font.pixelSize: 15; font.bold: true; color: Theme.token("color-text-primary", root.dark) }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 38; radius: 8; color: Theme.token("color-bg-subtle", root.dark)
                Label { anchors.verticalCenter: parent.verticalCenter; x: 14; font.pixelSize: 12; font.family: Theme.fontFamily.mono; color: Theme.token("color-text-primary", root.dark)
                    text: 'UiPopup { width: 300; height: 200;  // 放任意 QML，就是一个统一风格面板' }
            }
            UiButton { text: "打开自定义面板"; dark: root.dark; variant: "primary"; onClicked: customPanel.open() }
        }

        Label { text: "MessageDialog 用于系统消息。FileDialog 选文件。自定义业务弹窗统一用 UiPopup。"; font.pixelSize: 12; color: root.primary; wrapMode: Text.Wrap; Layout.fillWidth: true }
    }

    // ---- Dialogs ----
    MessageDialog { id: msgDialog; title: "消息"; text: "这是一条来自 QML 的消息弹窗。"; buttons: MessageDialog.Ok; onAccepted: root.dialogResult = "用户点击了 OK" }
    FileDialog { id: filePickDialog; fileMode: FileDialog.OpenFile; title: "选择一个文件"; onAccepted: { root.filePath = decodeURIComponent(selectedFile.toString()).replace("file:///", "") } }
    UiPopup { id: customPanel; width: 300; height: 180; anchors.centerIn: Overlay.overlay; dark: root.dark; surfaceRadius: Theme.radii.xl; surfaceFillColor: Theme.token("color-bg-surface", root.dark); surfaceBorderColor: Theme.token("color-border-default", root.dark)
        ColumnLayout { anchors.fill: parent; anchors.margins: 16; spacing: 12
            Label { text: "自定义弹窗"; font.pixelSize: 16; font.bold: true; color: Theme.token("color-text-primary", root.dark) }
            Label { text: "这里可以放任何 QML 组件：表单、列表、图片……"; font.pixelSize: 13; color: Theme.token("color-text-secondary", root.dark); Layout.fillWidth: true; wrapMode: Text.Wrap }
            UiButton { text: "关闭"; dark: root.dark; variant: "primary"; Layout.alignment: Qt.AlignHCenter; onClicked: customPanel.close() } } }
}
