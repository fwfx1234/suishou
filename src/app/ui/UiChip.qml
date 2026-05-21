import QtQuick
import QtQuick.Controls
import "../theme"

Rectangle {
    id: root
    property bool dark: false
    property string text: ""
    property bool selected: false
    property bool chipEnabled: true
    signal clicked()

    implicitWidth: label.implicitWidth + 18
    implicitHeight: 24
    radius: 12
    opacity: chipEnabled ? 1.0 : 0.5
    color: selected ? Theme.token("color-primary-bg", dark) : (hit.containsMouse ? Theme.token("color-bg-subtle-2", dark) : Theme.token("color-bg-subtle", dark))
    border.width: selected ? 1 : 0
    border.color: Theme.token("color-primary-active", dark)

    Label {
        id: label
        anchors.centerIn: parent
        text: root.text
        color: root.selected ? Theme.token("color-primary-active", root.dark) : Theme.token("color-text-regular", root.dark)
        font.pixelSize: Theme.fontSize.caption
        font.family: Theme.fontFamily.ui
    }

    MouseArea {
        id: hit
        anchors.fill: parent
        enabled: root.chipEnabled
        hoverEnabled: true
        cursorShape: root.chipEnabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: root.clicked()
    }
}
