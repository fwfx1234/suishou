import QtQuick
import "../theme"

Rectangle {
    id: root

    property bool dark: false
    property string text: ""
    property string shortcutText: ""
    property string leftIcon: ""
    property bool checked: false
    property bool reserveCheckSpace: false
    property bool destructive: false
    property bool itemEnabled: true
    property bool highlighted: false
    property color textColorOverride: "transparent"

    signal triggered()

    readonly property color macAccent: Theme.token("color-primary-active", root.dark)
    readonly property bool onAccent: (mouse.containsMouse && root.itemEnabled) || root.highlighted
    readonly property color textNormal: root.destructive
        ? Theme.token("color-danger", root.dark)
        : (root.textColorOverride.a > 0
            ? root.textColorOverride
            : Theme.token("color-text-primary", root.dark))
    readonly property color textMuted: Theme.token("color-text-secondary", root.dark)
    readonly property color textOnAccent: "#FFFFFF"
    readonly property color resolvedText: root.onAccent ? root.textOnAccent : root.textNormal
    readonly property color resolvedMuted: root.onAccent ? root.textOnAccent : root.textMuted

    implicitHeight: 26
    radius: 5
    color: root.onAccent ? root.macAccent : "transparent"
    opacity: root.itemEnabled ? 1.0 : 0.4
    antialiasing: true

    Item {
        id: checkSlot
        width: (root.checked || root.reserveCheckSpace) ? 16 : 0
        height: parent.height
        anchors.left: parent.left
        anchors.leftMargin: width > 0 ? 5 : 0

        Text {
            anchors.centerIn: parent
            visible: root.checked
            text: "✓"
            font.pixelSize: 11
            font.family: Theme.fontFamily.ui
            color: root.resolvedText
        }
    }

    UiIcon {
        id: iconSlot
        visible: root.leftIcon.length > 0
        width: visible ? 13 : 0
        height: 13
        iconSize: 13
        anchors.left: checkSlot.right
        anchors.leftMargin: visible ? 5 : 0
        anchors.verticalCenter: parent.verticalCenter
        name: root.leftIcon
        color: root.resolvedText
    }

    Text {
        id: shortcutLabel
        visible: root.shortcutText.length > 0
        anchors.right: parent.right
        anchors.rightMargin: 9
        anchors.verticalCenter: parent.verticalCenter
        text: root.shortcutText
        font.pixelSize: 11
        font.family: Theme.fontFamily.ui
        color: root.resolvedMuted
    }

    Text {
        id: titleLabel
        anchors.left: iconSlot.visible ? iconSlot.right : (checkSlot.width > 0 ? checkSlot.right : parent.left)
        anchors.leftMargin: iconSlot.visible ? 6 : (checkSlot.width > 0 ? 6 : 9)
        anchors.right: shortcutLabel.visible ? shortcutLabel.left : parent.right
        anchors.rightMargin: shortcutLabel.visible ? 9 : 9
        anchors.verticalCenter: parent.verticalCenter
        text: root.text
        font.pixelSize: 13
        font.family: Theme.fontFamily.ui
        color: root.resolvedText
        elide: Text.ElideRight
        verticalAlignment: Text.AlignVCenter
    }

    implicitWidth: titleLabel.implicitWidth
        + (iconSlot.visible ? iconSlot.width + 6 : 0)
        + (checkSlot.width > 0 ? checkSlot.width + 6 : 0)
        + (shortcutLabel.visible ? shortcutLabel.implicitWidth + 12 : 0)
        + 18

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: root.itemEnabled
        cursorShape: root.itemEnabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: if (root.itemEnabled) root.triggered()
    }
}
