import QtQuick
import "../theme"

Rectangle {
    id: root
    property bool dark: false
    property bool selected: false
    property bool elevated: false
    property color fillColor: elevated ? Theme.token("color-bg-elevated", dark) : Theme.token("color-bg-surface", dark)

    radius: Theme.radii.md
    color: selected ? Theme.token("color-row-selected", dark) : fillColor
    border.width: 1
    border.color: selected ? Theme.token("color-primary-active", dark) : Theme.token("color-border-default", dark)
    antialiasing: true
}
