import QtQuick
import "../theme"

Rectangle {
    id: root
    property bool dark: false
    property color fillColor: Theme.token("color-bg-surface", dark)

    radius: Theme.radii.lg
    color: fillColor
    border.width: 1
    border.color: Theme.token("color-border-default", dark)
    antialiasing: true
}
