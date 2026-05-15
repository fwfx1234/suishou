import QtQuick
import QtQuick.Controls
import "../theme"

Rectangle {
    id: root

    property bool dark: false
    property bool toggled: false
    property string checkedText: "⟨"
    property string uncheckedText: "⟩"
    signal toggleRequested(bool checked)

    implicitHeight: Theme.space["3"] * 2 + 6
    radius: Theme.radii.md
    color: Theme.token("color-bg-subtle", dark)

    MouseArea {
        id: hit
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.toggleRequested(!root.toggled)
    }

    Label {
        anchors.centerIn: parent
        text: root.toggled ? root.checkedText : root.uncheckedText
        font.pixelSize: Theme.fontSize.heading
        font.family: Theme.fontFamily.ui
        color: Theme.token("color-text-regular", root.dark)
    }

    ToolTip.visible: hit.containsMouse
    ToolTip.text: root.toggled ? "展开侧栏" : "收起侧栏"
    ToolTip.delay: 250
}
