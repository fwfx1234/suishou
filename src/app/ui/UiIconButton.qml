import QtQuick
import QtQuick.Controls
import "../theme"

Rectangle {
    id: root

    property bool dark: false
    property string iconName: ""
    property bool useQtaIcon: true
    property bool accent: false
    property bool danger: false
    property bool checked: false
    property string tooltip: ""
    property int iconSize: 16
    property int controlSize: 30

    signal clicked()

    implicitWidth: controlSize
    implicitHeight: controlSize
    radius: Theme.radii.md
    opacity: enabled ? 1.0 : 0.45
    color: {
        if (checked || accent)
            return root.dark ? Theme.token("color-primary-soft", true) : Theme.token("color-primary-bg", false)
        if (hit.pressed)
            return Theme.token("color-bg-subtle", root.dark)
        if (hit.containsMouse)
            return Theme.token("color-bg-subtle-2", root.dark)
        return "transparent"
    }
    border.width: checked || accent ? 1 : 0
    border.color: Theme.token("color-primary-active", root.dark)
    antialiasing: true

    UiIcon {
        anchors.centerIn: parent
        width: root.iconSize
        height: root.iconSize
        iconSize: root.iconSize
        name: root.iconName
        useQta: root.useQtaIcon
        color: root.danger
            ? Theme.token("color-danger", root.dark)
            : ((root.checked || root.accent) ? Theme.token("color-primary-active", root.dark) : Theme.token("color-text-regular", root.dark))
    }

    MouseArea {
        id: hit
        anchors.fill: parent
        enabled: root.enabled
        hoverEnabled: true
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: root.clicked()
    }

    ToolTip.visible: root.tooltip.length > 0 && hit.containsMouse
    ToolTip.text: root.tooltip
    ToolTip.delay: 300
}
