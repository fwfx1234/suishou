import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Rectangle {
    id: root

    property bool dark: false
    property bool collapsed: false
    property bool active: false
    property string menuText: ""
    property string menuIcon: ""
    property color highlightColor: Theme.token("color-primary-active", dark)
    signal activated()

    // 展开 / 收起同一行高，仅通过隐藏文字区分
    implicitHeight: Theme.space["3"] * 3
    radius: root.collapsed ? Theme.radii.xs : Theme.radii.sm
    color: "transparent"

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.space["2"]
        anchors.rightMargin: Theme.space["2"]
        spacing: Theme.space["2"]

        Rectangle {
            Layout.preferredWidth: 30
            Layout.preferredHeight: 30
            Layout.alignment: Qt.AlignVCenter
            radius: Theme.radii.xs
            color: "transparent"

            UiNavIcon {
                anchors.centerIn: parent
                name: root.menuIcon
                active: root.active
                dark: root.dark
                highlightColor: root.highlightColor
            }
        }

        Label {
            id: titleLabel
            text: root.menuText
            visible: !root.collapsed
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            color: root.active
                ? root.highlightColor
                : Theme.token("color-nav-idle", root.dark)
            font.pixelSize: Theme.fontSize.nav
            font.family: Theme.fontFamily.ui
            elide: Text.ElideRight
        }
    }

    MouseArea {
        id: navMouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.activated()
    }

    ToolTip.visible: root.collapsed && navMouse.containsMouse
    ToolTip.text: root.menuText
    ToolTip.delay: 350
}
