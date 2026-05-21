import QtQuick
import "../theme"

TextEdit {
    id: control

    property bool dark: false
    property bool framed: false
    property bool hoverEnabled: true
    property string placeholderText: ""
    property color placeholderTextColor: Theme.token("color-text-secondary", dark)

    readonly property bool hovered: hoverProbe.hovered

    selectByMouse: true
    persistentSelection: true
    color: Theme.token("color-text-primary", dark)
    selectedTextColor: "#FFFFFF"
    selectionColor: Theme.token("color-primary-active", dark)
    font.pixelSize: Theme.fontSize.body
    font.family: Theme.fontFamily.mono
    leftPadding: framed ? Theme.space["2.5"] : 0
    rightPadding: framed ? Theme.space["2.5"] : 0
    topPadding: framed ? Theme.space["2"] : 0
    bottomPadding: framed ? Theme.space["2"] : 0

    Rectangle {
        anchors.fill: parent
        visible: control.framed
        z: -1
        radius: Theme.radii.md
        color: Theme.token("color-bg-surface", control.dark)
        border.width: control.activeFocus ? 2 : (control.hovered ? 1 : 0)
        border.color: control.activeFocus
            ? Theme.token("color-primary-active", control.dark)
            : (control.hovered ? Theme.token("color-border-default", control.dark) : "transparent")
        antialiasing: true
    }

    Text {
        z: 1
        visible: control.text.length === 0 && control.placeholderText.length > 0 && control.preeditText.length === 0
        anchors.left: parent.left
        anchors.leftMargin: control.leftPadding
        anchors.right: parent.right
        anchors.rightMargin: control.rightPadding
        anchors.top: parent.top
        anchors.topMargin: control.topPadding
        text: control.placeholderText
        color: control.placeholderTextColor
        font: control.font
        elide: Text.ElideRight
        renderType: Text.NativeRendering
    }

    HoverHandler {
        id: hoverProbe
        enabled: control.hoverEnabled
    }

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.RightButton
        onPressed: function(mouse) {
            control.forceActiveFocus()
            if ((control.selectedText || "").length === 0)
                control.cursorPosition = control.positionAt(mouse.x, mouse.y)
            uiTextEditMenu.openAt(control, mouse.x, mouse.y)
            mouse.accepted = true
        }
    }

    UiTextEditMenu {
        id: uiTextEditMenu
        target: control
        dark: control.dark
    }
}
