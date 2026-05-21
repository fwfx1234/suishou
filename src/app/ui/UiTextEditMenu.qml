import QtQuick

UiMenuPopup {
    id: root

    property var target: null

    width: 176

    readonly property bool _readOnly: target ? target.readOnly === true : false
    readonly property bool _hasSelection: target ? (target.selectedText || "").length > 0 : false
    readonly property bool _canUndo: target ? target.canUndo === true : false
    readonly property bool _canRedo: target ? target.canRedo === true : false
    readonly property bool _canPaste: target ? target.canPaste === true : false

    contentItem: Column {
        id: column
        spacing: 0

        UiMenuItem {
            width: root.width - 8
            dark: root.dark
            text: "撤销"
            itemEnabled: root._canUndo && !root._readOnly
            onTriggered: { if (root.target) root.target.undo(); root.close() }
        }
        UiMenuItem {
            width: root.width - 8
            dark: root.dark
            text: "重做"
            itemEnabled: root._canRedo && !root._readOnly
            onTriggered: { if (root.target) root.target.redo(); root.close() }
        }
        UiMenuSeparator { width: root.width - 8; dark: root.dark }
        UiMenuItem {
            width: root.width - 8
            dark: root.dark
            text: "剪切"
            itemEnabled: root._hasSelection && !root._readOnly
            onTriggered: { if (root.target) root.target.cut(); root.close() }
        }
        UiMenuItem {
            width: root.width - 8
            dark: root.dark
            text: "复制"
            itemEnabled: root._hasSelection
            onTriggered: { if (root.target) root.target.copy(); root.close() }
        }
        UiMenuItem {
            width: root.width - 8
            dark: root.dark
            text: "粘贴"
            itemEnabled: root._canPaste && !root._readOnly
            onTriggered: { if (root.target) root.target.paste(); root.close() }
        }
        UiMenuSeparator { width: root.width - 8; dark: root.dark }
        UiMenuItem {
            width: root.width - 8
            dark: root.dark
            text: "全选"
            itemEnabled: root.target && ((root.target.length || 0) > 0 || (root.target.text || "").length > 0)
            onTriggered: { if (root.target) root.target.selectAll(); root.close() }
        }
    }
}
