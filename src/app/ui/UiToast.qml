import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Rectangle {
    id: root
    property bool dark: false
    property string text: ""
    property string iconName: "mdi6.check-circle-outline"

    parent: Overlay.overlay
    width: Math.min(parent ? parent.width - 32 : 360, Math.max(260, message.implicitWidth + 58))
    height: 44
    radius: Theme.radii.md
    color: Theme.token("color-bg-elevated", dark)
    border.width: 1
    border.color: Theme.token("color-border-default", dark)
    opacity: 0
    visible: opacity > 0
    z: 1000

    function show(messageText) {
        text = String(messageText || "")
        opacity = 0.98
        timer.restart()
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.space["3"]
        anchors.rightMargin: Theme.space["3"]
        spacing: Theme.space["2"]

        UiIcon {
            Layout.preferredWidth: 16
            Layout.preferredHeight: 16
            iconSize: 16
            name: root.iconName
            color: Theme.token("color-primary-active", root.dark)
        }

        Label {
            id: message
            Layout.fillWidth: true
            text: root.text
            color: Theme.token("color-text-primary", root.dark)
            font.pixelSize: Theme.fontSize.body
            elide: Text.ElideRight
        }
    }

    Behavior on opacity { NumberAnimation { duration: 140 } }
    Timer {
        id: timer
        interval: 2400
        onTriggered: root.opacity = 0
    }
}
