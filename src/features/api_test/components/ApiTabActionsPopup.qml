import QtQuick
import "../../../app/ui"

UiMenuPopup {
    id: root

    property color panelBg: "#FFFFFF"

    signal closeAllRequested()
    signal closeCurrentRequested()
    signal closeOthersRequested()

    width: 178
    padding: 5
    surfaceFillColor: root.panelBg

    contentItem: Column {
        spacing: 0

        UiMenuItem {
            width: root.width - root.leftPadding - root.rightPadding
            dark: root.dark
            text: "关闭全部标签页"
            leftIcon: "mdi6.close-box-multiple-outline"
            onTriggered: {
                root.closeAllRequested()
                root.close()
            }
        }

        UiMenuItem {
            width: root.width - root.leftPadding - root.rightPadding
            dark: root.dark
            text: "关闭当前标签页"
            leftIcon: "mdi6.close"
            onTriggered: {
                root.closeCurrentRequested()
                root.close()
            }
        }

        UiMenuItem {
            width: root.width - root.leftPadding - root.rightPadding
            dark: root.dark
            text: "关闭其它标签页"
            leftIcon: "mdi6.tab-remove"
            onTriggered: {
                root.closeOthersRequested()
                root.close()
            }
        }
    }
}
