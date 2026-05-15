import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../app/ui"
import "../../app/theme"

Item {
    property bool running: false
    property var rows: []
    readonly property bool dark: app.theme === "dark"
    readonly property color panelBg: Theme.token("color-bg-surface", dark)
    readonly property color panelBorder: Theme.token("color-border-default", dark)
    readonly property color textMain: Theme.token("color-text-primary", dark)
    readonly property color textMuted: Theme.token("color-text-regular", dark)
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space["3"]
        spacing: Theme.space["2"]
        Label { text: "抓包工具"; font.bold: true; font.pixelSize: Theme.fontSize.title; color: textMain; font.family: Theme.fontFamily.ui }
        RowLayout {
            Label { text: running ? "● 代理运行中" : "● 代理已停止"; color: running ? Theme.token("color-success", dark) : Theme.token("color-danger", dark) }
            UiButton {
                text: running ? "停止代理" : "启动代理"
                dark: dark
                variant: "primary"
                onClicked: {
                    running = !running
                    if (running)
                        packetCaptureVm.startPacketCapture()
                    else
                        packetCaptureVm.stopPacketCapture()
                }
            }
            UiButton {
                text: "清空"
                dark: dark
                variant: "secondary"
                onClicked: packetCaptureVm.clearPacketRows()
            }
            Label { text: "请求数: " + rows.length; color: textMuted }
        }
        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: rows
            delegate: Rectangle {
                width: ListView.view.width
                height: Theme.space["3"] * 3
                color: index % 2 === 0 ? panelBg : Theme.token("color-bg-subtle-2", dark)
                border.color: "transparent"
                radius: Theme.radii.md
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.space["2"]
                    anchors.rightMargin: Theme.space["2"]
                    Label { text: modelData.method; Layout.preferredWidth: 60; color: Theme.token("color-primary-active", dark); font.bold: true }
                    Label {
                        text: modelData.path
                        Layout.fillWidth: true
                        color: textMain
                        elide: Text.ElideMiddle
                    }
                    Label { text: modelData.status; Layout.preferredWidth: 60; color: Number(modelData.status) >= 400 ? Theme.token("color-danger", dark) : Theme.token("color-success", dark) }
                    Label { text: modelData.size; Layout.preferredWidth: 70; color: textMuted }
                }
            }
        }
    }

    Connections {
        target: packetCaptureVm
        function onPacketRowsUpdated(items) {
            rows = items
        }
    }
}
