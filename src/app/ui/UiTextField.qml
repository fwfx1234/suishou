import QtQuick
import "../theme"

FocusScope {
    id: control

    property bool dark: false
    property bool hoverEnabled: true
    property string placeholderText: ""
    property color placeholderTextColor: Theme.token("color-text-secondary", dark)
    property Item background: defaultBackground

    property alias text: editor.text
    property alias length: editor.length
    property alias displayText: editor.displayText
    property alias preeditText: editor.preeditText
    property alias color: editor.color
    property alias selectedTextColor: editor.selectedTextColor
    property alias selectionColor: editor.selectionColor
    property alias font: editor.font
    property alias horizontalAlignment: editor.horizontalAlignment
    property alias verticalAlignment: editor.verticalAlignment
    property alias wrapMode: editor.wrapMode
    property alias readOnly: editor.readOnly
    property alias cursorVisible: editor.cursorVisible
    property alias cursorPosition: editor.cursorPosition
    property alias cursorRectangle: editor.cursorRectangle
    property alias selectionStart: editor.selectionStart
    property alias selectionEnd: editor.selectionEnd
    property alias selectedText: editor.selectedText
    property alias maximumLength: editor.maximumLength
    property alias validator: editor.validator
    property alias inputMask: editor.inputMask
    property alias inputMethodHints: editor.inputMethodHints
    property alias acceptableInput: editor.acceptableInput
    property alias echoMode: editor.echoMode
    property alias activeFocusOnPress: editor.activeFocusOnPress
    property alias passwordCharacter: editor.passwordCharacter
    property alias passwordMaskDelay: editor.passwordMaskDelay
    property alias selectByMouse: editor.selectByMouse
    property alias mouseSelectionMode: editor.mouseSelectionMode
    property alias persistentSelection: editor.persistentSelection
    property alias canPaste: editor.canPaste
    property alias canUndo: editor.canUndo
    property alias canRedo: editor.canRedo
    property alias contentWidth: editor.contentWidth
    property alias contentHeight: editor.contentHeight
    property alias padding: editor.padding
    property alias leftPadding: editor.leftPadding
    property alias rightPadding: editor.rightPadding
    property alias topPadding: editor.topPadding
    property alias bottomPadding: editor.bottomPadding
    property alias renderType: editor.renderType

    readonly property bool hovered: hoverProbe.hovered

    implicitHeight: 30
    implicitWidth: 180
    clip: true

    signal accepted()
    signal editingFinished()
    signal textEdited()

    onBackgroundChanged: syncBackground()
    Component.onCompleted: syncBackground()
    onActiveFocusChanged: {
        if (activeFocus && !editor.activeFocus)
            editor.forceActiveFocus()
    }

    function syncBackground() {
        if (!control.background)
            return
        control.background.parent = control
        control.background.z = -2
        control.background.anchors.fill = control
    }

    Rectangle {
        id: defaultBackground
        visible: control.background === defaultBackground
        z: -2
        anchors.fill: parent
        radius: Theme.radii.md
        color: control.dark ? Theme.token("color-nav-icon-idle-bg", true) : Theme.token("color-bg-surface", false)
        border.width: control.activeFocus ? 2 : (control.hovered ? 1 : 0)
        border.color: control.activeFocus
            ? Theme.token("color-primary-active", control.dark)
            : (control.hovered ? Theme.token("color-border-default", control.dark) : "transparent")
        antialiasing: true
    }

    TextInput {
        id: editor
        anchors.fill: parent
        focus: true
        enabled: control.enabled
        Keys.forwardTo: [control]
        selectByMouse: true
        persistentSelection: true
        color: Theme.token("color-text-primary", control.dark)
        selectedTextColor: "#FFFFFF"
        selectionColor: Theme.token("color-primary-active", control.dark)
        font.pixelSize: Theme.fontSize.body
        font.family: Theme.fontFamily.ui
        verticalAlignment: TextInput.AlignVCenter
        leftPadding: Theme.space["2.5"]
        rightPadding: Theme.space["2.5"]
        clip: true
        onAccepted: control.accepted()
        onEditingFinished: control.editingFinished()
        onTextEdited: control.textEdited()
    }

    Text {
        z: 1
        visible: control.text.length === 0 && control.placeholderText.length > 0 && control.preeditText.length === 0
        anchors.left: parent.left
        anchors.leftMargin: control.leftPadding
        anchors.right: parent.right
        anchors.rightMargin: control.rightPadding
        anchors.verticalCenter: parent.verticalCenter
        text: control.placeholderText
        color: control.placeholderTextColor
        font: control.font
        elide: Text.ElideRight
        verticalAlignment: Text.AlignVCenter
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
            editor.forceActiveFocus()
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

    function selectAll() { editor.selectAll() }
    function selectWord() { editor.selectWord() }
    function select(start, end) { editor.select(start, end) }
    function deselect() { editor.deselect() }
    function cut() { editor.cut() }
    function copy() { editor.copy() }
    function paste() { editor.paste() }
    function undo() { editor.undo() }
    function redo() { editor.redo() }
    function insert(position, value) { editor.insert(position, value) }
    function remove(start, end) { editor.remove(start, end) }
    function clear() { editor.clear() }
    function positionAt(x, y, position) {
        if (position !== undefined)
            return editor.positionAt(x, y, position)
        return editor.positionAt(x, y)
    }
    function positionToRectangle(pos) { return editor.positionToRectangle(pos) }
    function moveCursorSelection(pos) { editor.moveCursorSelection(pos) }
}
