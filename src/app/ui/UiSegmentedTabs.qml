pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    property bool dark: false
    property var tabs: []
    property var counts: []
    property int currentIndex: 0
    property bool showIcons: true
    property bool showZeroCount: false
    property int controlHeight: 28
    property int minItemWidth: 58
    property int itemPaddingX: Theme.space["2.5"]
    property color accentColor: Theme.token("color-primary-active", dark)
    property color textColor: Theme.token("color-text-regular", dark)
    property color mutedColor: Theme.token("color-text-secondary", dark)
    property color surfaceColor: Theme.token("color-bg-surface", dark)
    property color trackColor: dark ? Qt.rgba(1, 1, 1, 0.055) : "#EEF0F4"
    property color hoverColor: dark ? Qt.rgba(1, 1, 1, 0.055) : Qt.rgba(1, 1, 1, 0.58)
    property color activeColor: dark ? Qt.rgba(1, 1, 1, 0.11) : "#FFFFFF"
    property color borderColor: dark ? Qt.rgba(1, 1, 1, 0.09) : Qt.rgba(60, 60, 67, 0.12)

    readonly property real contentPreferredWidth: segmentFrame.width

    signal activated(int index)

    implicitWidth: contentPreferredWidth
    implicitHeight: controlHeight + 4

    function countAt(index) {
        if (!root.counts || index < 0 || index >= root.counts.length)
            return 0
        var value = Number(root.counts[index])
        return isNaN(value) ? 0 : value
    }

    function titleAt(item) {
        return item ? (item.title || item.text || "") : ""
    }

    function iconAt(item) {
        return item ? (item.icon || item.iconName || "") : ""
    }

    Flickable {
        anchors.fill: parent
        clip: true
        interactive: contentWidth > width
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: segmentFrame.width
        contentHeight: height

        Rectangle {
            id: segmentFrame
            width: segmentRow.implicitWidth + 4
            height: root.controlHeight
            anchors.verticalCenter: parent.verticalCenter
            radius: 9
            color: root.trackColor
            border.width: 1
            border.color: root.borderColor
            antialiasing: true

            Row {
                id: segmentRow
                anchors.fill: parent
                anchors.margins: 2
                spacing: 1

                Repeater {
                    model: root.tabs

                    delegate: Rectangle {
                        id: segment

                        required property int index
                        required property var modelData

                        property bool active: segment.index === root.currentIndex
                        property int itemCount: root.countAt(segment.index)

                        width: Math.max(root.minItemWidth, segmentContent.implicitWidth + root.itemPaddingX * 2)
                        height: parent.height
                        radius: 7
                        color: active ? root.activeColor : (segmentMouse.containsMouse ? root.hoverColor : "transparent")
                        border.width: active ? 1 : 0
                        border.color: root.dark ? Qt.rgba(1, 1, 1, 0.11) : Qt.rgba(60, 60, 67, 0.10)
                        antialiasing: true

                        Row {
                            id: segmentContent
                            anchors.centerIn: parent
                            spacing: 5

                            UiIcon {
                                visible: root.showIcons && root.iconAt(segment.modelData).length > 0
                                width: 14
                                height: 14
                                iconSize: 14
                                name: root.iconAt(segment.modelData)
                                color: segment.active ? root.accentColor : root.mutedColor
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Label {
                                text: root.titleAt(segment.modelData)
                                color: segment.active ? Theme.token("color-text-primary", root.dark) : root.textColor
                                font.pixelSize: Theme.fontSize.caption
                                font.weight: segment.active ? Font.DemiBold : Font.Normal
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Rectangle {
                                visible: root.showZeroCount || segment.itemCount > 0
                                width: Math.max(16, countLabel.implicitWidth + 8)
                                height: 15
                                radius: 7
                                color: segment.active
                                    ? Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, root.dark ? 0.18 : 0.10)
                                    : (root.dark ? Qt.rgba(1, 1, 1, 0.07) : Qt.rgba(60, 60, 67, 0.08))
                                anchors.verticalCenter: parent.verticalCenter

                                Label {
                                    id: countLabel
                                    anchors.centerIn: parent
                                    text: segment.itemCount
                                    color: segment.active ? root.accentColor : root.mutedColor
                                    font.pixelSize: 10
                                    font.family: Theme.fontFamily.mono
                                    font.weight: Font.DemiBold
                                }
                            }
                        }

                        MouseArea {
                            id: segmentMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.activated(segment.index)
                        }
                    }
                }
            }
        }
    }
}
