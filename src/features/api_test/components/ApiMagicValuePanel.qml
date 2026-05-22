pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../app/ui"
import "../../../app/theme"

Rectangle {
    id: root

    property bool dark: false
    property color panelBg: "#FFFFFF"
    property color panelBorder: "#D0D7DE"
    property color textMain: "#333333"
    property color textMuted: "#666666"
    property color textSubtle: Theme.token("color-text-secondary", dark)
    readonly property color rowHover: dark ? Qt.rgba(1, 1, 1, 0.055) : Qt.rgba(0, 0, 0, 0.035)
    readonly property color subtleFill: dark ? Qt.rgba(1, 1, 1, 0.045) : Qt.rgba(0, 0, 0, 0.028)
    readonly property color accentSoft: dark ? Qt.rgba(0.04, 0.52, 1, 0.16) : Qt.rgba(0.04, 0.52, 1, 0.09)
    readonly property color accentBorder: dark ? Qt.rgba(0.04, 0.52, 1, 0.24) : Qt.rgba(0.04, 0.52, 1, 0.14)
    property var items: [
        { group: "时间", title: "时间戳", desc: "Unix 秒级时间戳", value: "{{$timestamp}}" },
        { group: "时间", title: "毫秒时间戳", desc: "Unix 毫秒时间戳", value: "{{$timestamp_ms}}" },
        { group: "时间", title: "ISO 时间", desc: "UTC ISO-8601 时间", value: "{{$iso_datetime}}" },
        { group: "时间", title: "日期", desc: "UTC 日期 yyyy-mm-dd", value: "{{$date}}" },
        { group: "时间", title: "日期时间", desc: "UTC yyyy-mm-dd HH:MM:SS", value: "{{$datetime}}" },
        { group: "时间", title: "时间", desc: "UTC HH:MM:SS", value: "{{$time}}" },
        { group: "时间", title: "年", desc: "UTC 四位年份", value: "{{$year}}" },
        { group: "时间", title: "月", desc: "UTC 两位月份", value: "{{$month}}" },
        { group: "时间", title: "日", desc: "UTC 两位日期", value: "{{$day}}" },
        { group: "随机", title: "UUID", desc: "随机 UUID v4", value: "{{$uuid}}" },
        { group: "随机", title: "短 UUID", desc: "无横线 UUID", value: "{{$uuid_simple}}" },
        { group: "随机", title: "随机整数", desc: "0 到 1000000", value: "{{$random_int}}" },
        { group: "随机", title: "4 位数字", desc: "1000 到 9999", value: "{{$random_4}}" },
        { group: "随机", title: "6 位数字", desc: "100000 到 999999", value: "{{$random_6}}" },
        { group: "随机", title: "8 位数字", desc: "10000000 到 99999999", value: "{{$random_8}}" },
        { group: "随机", title: "随机布尔", desc: "true 或 false", value: "{{$random_bool}}" },
        { group: "随机", title: "随机字符串", desc: "12 位字母数字", value: "{{$random_string}}" },
        { group: "随机", title: "随机 Hex", desc: "16 位十六进制", value: "{{$random_hex}}" },
        { group: "随机", title: "随机邮箱", desc: "example.com 测试邮箱", value: "{{$random_email}}" },
        { group: "随机", title: "随机 Base64", desc: "随机字符串的 Base64", value: "{{$base64_random}}" },
        { group: "变量", title: "环境变量", desc: "读取环境管理中的变量", value: "{{token}}" }
    ]

    signal insertRequested(string valueText)
    signal closeRequested()

    radius: 12
    color: root.panelBg
    border.width: 1
    border.color: root.dark ? Qt.rgba(1, 1, 1, 0.08) : Qt.rgba(0, 0, 0, 0.07)
    clip: true

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            color: "transparent"
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.space["3"]
                anchors.rightMargin: Theme.space["2"]
                spacing: Theme.space["2.5"]

                Rectangle {
                    Layout.preferredWidth: 24
                    Layout.preferredHeight: 24
                    radius: Theme.radii.sm
                    color: root.accentSoft
                    border.width: 1
                    border.color: root.accentBorder

                    UiIcon {
                        anchors.centerIn: parent
                        width: 14
                        height: 14
                        iconSize: 14
                        useQta: true
                        name: "mdi6.magic-staff"
                        color: Theme.token("color-primary-active", root.dark)
                    }
                }

                Label {
                    text: "插入变量"
                    color: root.textMain
                    font.pixelSize: Theme.fontSize.body
                    font.weight: Font.DemiBold
                    Layout.fillWidth: true
                }

                UiIconButton {
                    dark: root.dark
                    controlSize: 26
                    iconSize: 14
                    iconName: "mdi6.close"
                    tooltip: "关闭"
                    onClicked: root.closeRequested()
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: root.dark ? Qt.rgba(1, 1, 1, 0.06) : Qt.rgba(0, 0, 0, 0.055)
        }

        Flickable {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentHeight: itemColumn.implicitHeight

            ColumnLayout {
                id: itemColumn
                width: parent.width
                spacing: 0

                Repeater {
                    model: root.items
                    delegate: Rectangle {
                        id: optionItem
                        required property var modelData

                        Layout.fillWidth: true
                        Layout.preferredHeight: 48
                        color: optionMouse.containsMouse ? root.rowHover : "transparent"

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.space["3"]
                            anchors.rightMargin: Theme.space["3"]
                            spacing: Theme.space["2.5"]

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Theme.space["1"]
                                    Rectangle {
                                        Layout.preferredWidth: groupLabel.implicitWidth + 10
                                        Layout.preferredHeight: 18
                                        radius: 9
                                        visible: groupLabel.text.length > 0
                                        color: root.subtleFill

                                        Label {
                                            id: groupLabel
                                            anchors.centerIn: parent
                                            text: optionItem.modelData.group || ""
                                            color: root.textSubtle
                                            font.pixelSize: 10
                                            font.weight: Font.Medium
                                        }
                                    }
                                    Label {
                                        Layout.fillWidth: true
                                        text: optionItem.modelData.title
                                        color: root.textMain
                                        font.pixelSize: Theme.fontSize.body
                                        elide: Text.ElideRight
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text: optionItem.modelData.desc
                                    color: root.textSubtle
                                    font.pixelSize: Theme.fontSize.caption
                                    elide: Text.ElideRight
                                }
                            }

                            Rectangle {
                                Layout.preferredWidth: Math.min(128, Math.max(valueLabel.implicitWidth + 14, 72))
                                Layout.preferredHeight: 24
                                radius: Theme.radii.sm
                                color: root.accentSoft
                                border.width: 1
                                border.color: root.accentBorder

                                Label {
                                    id: valueLabel
                                    anchors.fill: parent
                                    anchors.leftMargin: Theme.space["1.5"]
                                    anchors.rightMargin: Theme.space["1.5"]
                                    text: optionItem.modelData.value
                                    color: Theme.token("color-primary-active", root.dark)
                                    font.family: Theme.fontFamily.mono
                                    font.pixelSize: 11
                                    verticalAlignment: Text.AlignVCenter
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideMiddle
                                }
                            }
                        }

                        MouseArea {
                            id: optionMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.insertRequested(optionItem.modelData.value)
                        }
                    }
                }
            }
        }
    }
}
