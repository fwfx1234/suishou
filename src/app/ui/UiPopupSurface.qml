import QtQuick
import QtQuick.Effects
import "../theme"

Item {
    id: root

    property bool dark: false
    property int radius: Theme.radii.lg
    property color fillColor: Theme.token("color-bg-surface", dark)
    MultiEffect {
        anchors.fill: surface
        source: surface
        shadowEnabled: true
        shadowBlur: 0.7
        shadowOpacity: 0.3
        shadowHorizontalOffset: 0
        shadowVerticalOffset: 2
    }

    Rectangle {
        id: surface
        anchors.fill: parent
        radius: root.radius
        color: root.fillColor
        border.width: 0
        border.color: "transparent"
    }
}
