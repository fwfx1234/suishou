import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../app/ui"
import "../../app/theme"

Item {
    readonly property bool dark: app.theme === "dark"
    readonly property color panelBg: Theme.token("color-bg-surface", dark)
    readonly property color panelBorder: Theme.token("color-border-default", dark)
    readonly property color textMain: Theme.token("color-text-primary", dark)
    readonly property color textMuted: Theme.token("color-text-regular", dark)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space["3"]
        spacing: Theme.space["2.5"]
        Label { text: "系统设置"; font.bold: true; font.pixelSize: Theme.fontSize.title; color: textMain; font.family: Theme.fontFamily.ui }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.space["3"] * 9
            radius: Theme.radii.xl
            color: panelBg
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.space["3"]
                Label { text: "主题模式"; font.bold: true; color: textMain }
                RowLayout {
                    RadioButton { text: "浅色"; checked: app.theme === "light"; onClicked: app.setTheme("light") }
                    RadioButton { text: "深色"; checked: app.theme === "dark"; onClicked: app.setTheme("dark") }
                }
                Label { text: "已启用本地数据存储"; color: textMuted }
            }
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.space["3"] * 12
            radius: Theme.radii.xl
            color: panelBg
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.space["3"]
                spacing: Theme.space["2"]
                Label { text: "开发诊断"; font.bold: true; color: textMain }
                Label { text: "数据目录：" + diagnostics.dataDir; color: textMuted; elide: Text.ElideMiddle; Layout.fillWidth: true }
                Label { text: "日志目录：" + diagnostics.logDir; color: textMuted; elide: Text.ElideMiddle; Layout.fillWidth: true }
                Label { text: "插件数量：" + diagnostics.pluginCount; color: textMuted }
                Label { text: "后台插件：" + diagnostics.backgroundPlugins; color: textMuted; wrapMode: Text.Wrap; Layout.fillWidth: true }
            }
        }
    }

    property var diagnostics: (typeof systemSettingsVm !== "undefined" && systemSettingsVm ? systemSettingsVm.diagnostics() : ({}))
}
