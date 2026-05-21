import QtQuick

Item {
    id: root
    property bool dark: false

    implicitHeight: 7

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: 7
        anchors.rightMargin: 7
        height: 1
        color: root.dark ? Qt.rgba(1, 1, 1, 0.07) : Qt.rgba(0, 0, 0, 0.07)
    }
}
