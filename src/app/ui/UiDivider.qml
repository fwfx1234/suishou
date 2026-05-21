import QtQuick
import "../theme"

Rectangle {
    id: root
    property bool dark: false
    property bool vertical: false
    implicitWidth: vertical ? 1 : 0
    implicitHeight: vertical ? 0 : 1
    color: Theme.token("color-border-default", dark)
}
