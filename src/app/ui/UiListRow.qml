import QtQuick
import "../theme"

Rectangle {
    id: root
    property bool dark: false
    property bool selected: false
    property bool rowEnabled: true
    property bool hovered: hit.containsMouse
    signal clicked()

    implicitHeight: 36
    radius: Theme.radii.sm
    opacity: rowEnabled ? 1.0 : 0.45
    color: selected ? Theme.token("color-row-selected", dark) : (hovered ? Theme.token("color-row-hover", dark) : "transparent")

    MouseArea {
        id: hit
        anchors.fill: parent
        enabled: root.rowEnabled
        hoverEnabled: true
        cursorShape: root.rowEnabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: root.clicked()
    }
}
