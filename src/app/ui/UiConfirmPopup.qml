import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

UiPopup {
    id: root
    property string title: "确认操作"
    property string message: ""
    property string acceptText: "确认"
    property string rejectText: "取消"
    property bool danger: false
    signal accepted()
    signal rejected()

    width: 360
    height: content.implicitHeight
    dark: false
    modal: true
    dim: true
    closePolicy: Popup.CloseOnEscape

    contentItem: ColumnLayout {
        id: content
        spacing: 0

        ColumnLayout {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.space["4"]
            Layout.rightMargin: Theme.space["4"]
            Layout.topMargin: Theme.space["4"]
            Layout.bottomMargin: Theme.space["3"]
            spacing: Theme.space["2"]

            Label {
                Layout.fillWidth: true
                text: root.title
                color: Theme.token("color-text-primary", root.dark)
                font.pixelSize: Theme.fontSize.heading
                font.weight: Font.DemiBold
            }
            Label {
                Layout.fillWidth: true
                text: root.message
                color: Theme.token("color-text-secondary", root.dark)
                font.pixelSize: Theme.fontSize.body
                wrapMode: Text.WordWrap
            }
        }

        UiDivider { Layout.fillWidth: true; dark: root.dark }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.space["4"]
            Layout.rightMargin: Theme.space["4"]
            Layout.topMargin: Theme.space["3"]
            Layout.bottomMargin: Theme.space["3"]
            spacing: Theme.space["2"]
            Item { Layout.fillWidth: true }
            UiButton {
                dark: root.dark
                text: root.rejectText
                variant: "ghost"
                onClicked: {
                    root.rejected()
                    root.close()
                }
            }
            UiButton {
                dark: root.dark
                text: root.acceptText
                variant: root.danger ? "secondary" : "primary"
                danger: root.danger
                onClicked: {
                    root.accepted()
                    root.close()
                }
            }
        }
    }
}
