import QtQuick
import QtQuick.Controls
import "../theme"

Rectangle {
    id: root
    property bool dark: false
    property string text: ""
    property color badgeColor: Theme.token("color-bg-subtle", dark)
    property color textColor: Theme.token("color-text-regular", dark)

    implicitWidth: label.implicitWidth + 10
    implicitHeight: 18
    radius: 5
    color: badgeColor

    Label {
        id: label
        anchors.centerIn: parent
        text: root.text
        color: root.textColor
        font.pixelSize: Theme.fontSize.caption
        font.family: Theme.fontFamily.ui
        font.weight: Font.Medium
    }
}
