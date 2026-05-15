import QtQuick
import QtQuick.Controls
import "../theme"

Slider {
    id: control

    property bool dark: false

    implicitHeight: Theme.space["4"] + Theme.space["2"]

    background: Rectangle {
        x: control.leftPadding
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: control.availableWidth
        height: Theme.space["1"] + 2
        radius: Theme.radii.sm / 2
        color: control.dark ? Theme.token("color-nav-icon-idle-bg", true) : Theme.token("color-border-default", false)

        Rectangle {
            width: control.visualPosition * parent.width
            height: parent.height
            radius: parent.radius
            color: Theme.token("color-primary", control.dark)
        }
    }

    handle: Rectangle {
        x: control.leftPadding + control.visualPosition * (control.availableWidth - width)
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: Theme.space["2.5"] + Theme.space["1"]
        height: Theme.space["2.5"] + Theme.space["1"]
        radius: width / 2
        color: control.pressed ? Theme.token("color-primary-active", control.dark) : Theme.token("color-primary-hover", control.dark)
    }
}
