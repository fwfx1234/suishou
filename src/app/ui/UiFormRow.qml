import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

RowLayout {
    id: root
    property bool dark: false
    property string label: ""
    property int labelWidth: 88
    spacing: Theme.space["2"]

    Label {
        text: root.label
        visible: root.label.length > 0
        color: Theme.token("color-text-secondary", root.dark)
        font.pixelSize: Theme.fontSize.body
        horizontalAlignment: Text.AlignRight
        Layout.preferredWidth: root.labelWidth
    }
}
