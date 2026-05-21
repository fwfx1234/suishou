import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

ColumnLayout {
    id: root
    property bool dark: false
    property string iconName: ""
    property string title: ""
    property string message: ""
    spacing: Theme.space["2"]

    UiIcon {
        visible: root.iconName.length > 0
        Layout.alignment: Qt.AlignHCenter
        Layout.preferredWidth: 32
        Layout.preferredHeight: 32
        iconSize: 32
        name: root.iconName
        color: Theme.token("color-text-secondary", root.dark)
    }

    Label {
        visible: root.title.length > 0
        Layout.alignment: Qt.AlignHCenter
        text: root.title
        color: Theme.token("color-text-regular", root.dark)
        font.pixelSize: Theme.fontSize.body
        font.weight: Font.Medium
    }

    Label {
        visible: root.message.length > 0
        Layout.alignment: Qt.AlignHCenter
        Layout.maximumWidth: 360
        text: root.message
        color: Theme.token("color-text-secondary", root.dark)
        font.pixelSize: Theme.fontSize.caption
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
    }
}
