import QtQuick
import QtQuick.Effects

Item {
    id: root

    property bool dark: false
    property int radius: 10
    property color fillColor: root.dark ? Qt.rgba(0.12, 0.13, 0.16, 0.96) : Qt.rgba(1, 1, 1, 0.98)
    property color borderColor: root.dark ? Qt.rgba(1, 1, 1, 0.10) : Qt.rgba(0, 0, 0, 0.08)

    MultiEffect {
        anchors.fill: surface
        source: surface
        shadowEnabled: true
        shadowBlur: 0.75
        shadowOpacity: root.dark ? 0.30 : 0.16
        shadowHorizontalOffset: 0
        shadowVerticalOffset: 8
        shadowColor: "#000000"
    }

    Rectangle {
        id: surface
        anchors.fill: parent
        radius: root.radius
        color: root.fillColor
        border.width: 1
        border.color: root.borderColor
        antialiasing: true
    }
}
