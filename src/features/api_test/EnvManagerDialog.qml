import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../app/ui"
import "../../app/theme"
import "components"

Dialog {
    id: dialog

    property bool dark: false
    property var environments: []
    property int currentEnvIndex: 0
    property var draftEnvironments: []
    property int selectedIndex: 0
    property int detailTab: 0
    property var activeRowEditor: null
    property var activeFieldEditor: null
    property bool autoSaveEnabled: false
    property color surface: Theme.token("color-bg-surface", dark)
    property color subtle: dark ? Theme.token("color-bg-subtle-2", true) : "#F5F6F8"
    property color panel: dark ? Theme.token("color-bg-subtle", true) : "#FAFBFC"
    property color sidebarSurface: dark ? Qt.rgba(1, 1, 1, 0.045) : "#F2F4F7"
    property color toolbarSurface: dark ? Qt.rgba(1, 1, 1, 0.035) : "#FBFBFD"
    property color hairline: dark ? Qt.rgba(1, 1, 1, 0.075) : Qt.rgba(60, 60, 67, 0.10)
    property color selectedFill: dark ? Qt.rgba(10, 132, 255, 0.18) : Qt.rgba(10, 132, 255, 0.12)
    property color borderColor: Theme.token("color-border-default", dark)
    property color textMain: Theme.token("color-text-primary", dark)
    property color textMuted: Theme.token("color-text-regular", dark)
    property color textSubtle: Theme.token("color-text-secondary", dark)
    property var detailTabs: [
        { title: "变量", kind: "variables", addText: "新增变量", keyTitle: "变量名", valueTitle: "变量值", emptyText: "暂无环境变量", icon: "mdi6.variable" },
        { title: "Headers", kind: "headers", addText: "新增 Header", keyTitle: "Header 名", valueTitle: "Header 值", emptyText: "暂无公共 Header", icon: "mdi6.format-header-pound" }
    ]

    signal environmentsSaved(var envs, int selectedIndex)

    modal: true
    title: ""
    standardButtons: Dialog.NoButton
    width: Math.min(980, Overlay.overlay ? Overlay.overlay.width * 0.76 : 980)
    height: Math.min(640, Overlay.overlay ? Overlay.overlay.height * 0.82 : 640)
    padding: 0

    function clone(value) {
        return JSON.parse(JSON.stringify(value || []))
    }

    function blankEnvironment(index) {
        return {
            id: "",
            name: index === 0 ? "默认环境" : ("新环境 " + index),
            baseUrl: "",
            variables: [],
            headers: []
        }
    }

    function normalizeRow(row) {
        return {
            enabled: row && row.enabled !== false,
            key: row ? (row.key || row.name || "") : "",
            value: row ? (row.value || row.localValue || "") : ""
        }
    }

    function normalizeRows(rows) {
        var out = []
        var list = rows || []
        for (var i = 0; i < list.length; i++) {
            var row = normalizeRow(list[i])
            if (row.key.length > 0 || row.value.length > 0)
                out.push(row)
        }
        return out
    }

    function normalizeEnvironment(env, index) {
        var item = env || blankEnvironment(index + 1)
        var name = (item.name === undefined || item.name === null) ? "" : ("" + item.name).trim()
        return {
            id: item.id || "",
            name: name,
            baseUrl: item.baseUrl || "",
            variables: normalizeRows(item.variables || []),
            headers: normalizeRows(item.headers || [])
        }
    }

    function resetDraft() {
        var source = clone(dialog.environments)
        var next = []
        for (var i = 0; i < source.length; i++)
            next.push(normalizeEnvironment(source[i], i))
        if (next.length === 0)
            next.push({
                id: "",
                name: "默认环境",
                baseUrl: "http://127.0.0.1:8000",
                variables: [],
                headers: []
            })
        dialog.draftEnvironments = next
        dialog.selectedIndex = Math.max(0, Math.min(dialog.currentEnvIndex, next.length - 1))
    }

    function disposePage() {
        autoSaveTimer.stop()
        close()
        environments = []
        draftEnvironments = []
        selectedIndex = -1
        detailTab = 0
        activeRowEditor = null
        activeFieldEditor = null
    }

    function currentEnvironment() {
        if (dialog.draftEnvironments.length === 0)
            return blankEnvironment(0)
        var idx = Math.max(0, Math.min(dialog.selectedIndex, dialog.draftEnvironments.length - 1))
        return dialog.draftEnvironments[idx]
    }

    function currentRows() {
        var tab = dialog.detailTabs[dialog.detailTab] || dialog.detailTabs[0]
        return currentEnvironment()[tab.kind] || []
    }

    function detailCounts() {
        var env = currentEnvironment()
        return [
            (env.variables || []).length,
            (env.headers || []).length
        ]
    }

    function updateCurrentEnvironment(field, value) {
        if (dialog.draftEnvironments.length === 0)
            return
        var list = clone(dialog.draftEnvironments)
        var env = list[dialog.selectedIndex]
        env[field] = value
        list[dialog.selectedIndex] = env
        dialog.draftEnvironments = list
    }

    function setActiveField(field, editor) {
        dialog.activeFieldEditor = {
            field: field,
            editor: editor
        }
    }

    function clearActiveField(editor) {
        if (dialog.activeFieldEditor && dialog.activeFieldEditor.editor === editor) {
            dialog.commitActiveField()
            dialog.activeFieldEditor = null
        }
    }

    function commitActiveField() {
        var item = dialog.activeFieldEditor
        if (!item || !item.editor)
            return
        if (item.field === "name")
            dialog.updateCurrentEnvironment("name", item.editor.text.trim())
        else if (item.field === "baseUrl")
            dialog.updateCurrentEnvironment("baseUrl", item.editor.text.trim())
    }

    function addEnvironment() {
        dialog.commitActiveField()
        dialog.commitActiveEditor()
        var list = clone(dialog.draftEnvironments)
        list.push(blankEnvironment(list.length + 1))
        dialog.draftEnvironments = list
        dialog.selectedIndex = list.length - 1
    }

    function duplicateCurrentEnvironment() {
        if (dialog.draftEnvironments.length === 0)
            return
        dialog.commitActiveField()
        var list = clone(dialog.draftEnvironments)
        var env = normalizeEnvironment(list[dialog.selectedIndex], dialog.selectedIndex)
        env.id = ""
        env.name = env.name + " 副本"
        list.splice(dialog.selectedIndex + 1, 0, env)
        dialog.draftEnvironments = list
        dialog.selectedIndex = dialog.selectedIndex + 1
    }

    function deleteCurrentEnvironment() {
        if (dialog.draftEnvironments.length === 0)
            return
        dialog.commitActiveField()
        dialog.commitActiveEditor()
        var list = clone(dialog.draftEnvironments)
        list.splice(dialog.selectedIndex, 1)
        if (list.length === 0)
            list.push(blankEnvironment(0))
        dialog.draftEnvironments = list
        dialog.selectedIndex = Math.max(0, Math.min(dialog.selectedIndex, list.length - 1))
    }

    function addRow(kind) {
        dialog.commitActiveField()
        dialog.commitActiveEditor()
        var list = clone(dialog.draftEnvironments)
        if (dialog.selectedIndex < 0 || dialog.selectedIndex >= list.length)
            return
        var env = list[dialog.selectedIndex]
        var rows = env[kind] || []
        rows.push({ enabled: true, key: "", value: "" })
        env[kind] = rows
        list[dialog.selectedIndex] = env
        dialog.draftEnvironments = list
    }

    function updateRow(kind, rowIndex, field, value) {
        var list = clone(dialog.draftEnvironments)
        if (dialog.selectedIndex < 0 || dialog.selectedIndex >= list.length)
            return
        var env = list[dialog.selectedIndex]
        var rows = env[kind] || []
        if (rowIndex < 0 || rowIndex >= rows.length)
            return
        rows[rowIndex][field] = value
        env[kind] = rows
        list[dialog.selectedIndex] = env
        dialog.draftEnvironments = list
    }

    function deleteRow(kind, rowIndex) {
        dialog.commitActiveField()
        dialog.commitActiveEditor()
        var list = clone(dialog.draftEnvironments)
        if (dialog.selectedIndex < 0 || dialog.selectedIndex >= list.length)
            return
        var env = list[dialog.selectedIndex]
        var rows = env[kind] || []
        if (rowIndex < 0 || rowIndex >= rows.length)
            return
        rows.splice(rowIndex, 1)
        env[kind] = rows
        list[dialog.selectedIndex] = env
        dialog.draftEnvironments = list
    }

    function setActiveEditor(kind, rowIndex, field, editor) {
        dialog.activeRowEditor = {
            kind: kind,
            rowIndex: rowIndex,
            field: field,
            editor: editor
        }
    }

    function clearActiveEditor(editor) {
        if (dialog.activeRowEditor && dialog.activeRowEditor.editor === editor) {
            dialog.commitActiveEditor()
            dialog.activeRowEditor = null
        }
    }

    function commitActiveEditor() {
        var item = dialog.activeRowEditor
        if (!item || !item.editor)
            return
        var value = item.field === "key" ? item.editor.text.trim() : item.editor.text
        dialog.updateRow(item.kind, item.rowIndex, item.field, value)
    }

    function cleanDraft() {
        var list = clone(dialog.draftEnvironments)
        var out = []
        for (var i = 0; i < list.length; i++)
            out.push(normalizeEnvironment(list[i], i))
        if (out.length === 0)
            out.push(blankEnvironment(0))
        return out
    }

    function save(closeAfter) {
        dialog.commitActiveField()
        dialog.commitActiveEditor()
        var envs = cleanDraft()
        dialog.draftEnvironments = envs
        dialog.selectedIndex = Math.max(0, Math.min(dialog.selectedIndex, envs.length - 1))
        dialog.environmentsSaved(envs, dialog.selectedIndex)
        if (closeAfter)
            dialog.close()
    }

    function scheduleAutoSave() {
        if (!dialog.autoSaveEnabled || !dialog.opened)
            return
        autoSaveTimer.restart()
    }

    onOpened: resetDraft()
    Component.onCompleted: resetDraft()
    onEnvironmentsChanged: {
        if (!dialog.opened)
            resetDraft()
    }

    Timer {
        id: autoSaveTimer
        interval: 300
        repeat: false
        onTriggered: dialog.save(false)
    }

    background: UiPopupSurface {
        dark: dialog.dark
        radius: Theme.radii.sheet
        fillColor: dialog.surface
        borderWidth: 1
        borderColor: dialog.dark ? Qt.rgba(1, 1, 1, 0.14) : Qt.rgba(0, 0, 0, 0.10)
    }

    contentItem: Rectangle {
        color: dialog.surface
        radius: Theme.radii.sheet
        clip: true
        antialiasing: true

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 48
                color: dialog.toolbarSurface
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.space["4"]
                    anchors.rightMargin: Theme.space["3"]
                    spacing: Theme.space["2"]

                    Label {
                        text: "环境管理"
                        Layout.fillWidth: true
                        color: dialog.textMain
                        font.pixelSize: 16
                        font.weight: Font.DemiBold
                    }

                    UiBadge {
                        text: dialog.draftEnvironments.length + " 个环境"
                        dark: dialog.dark
                        badgeColor: dialog.dark ? Qt.rgba(1, 1, 1, 0.07) : Qt.rgba(60, 60, 67, 0.08)
                        textColor: dialog.textSubtle
                    }

                    UiIconButton {
                        dark: dialog.dark
                        controlSize: 28
                        iconSize: 14
                        iconName: "mdi6.close"
                        tooltip: "关闭"
                        onClicked: dialog.close()
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: dialog.hairline }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                Rectangle {
                    Layout.preferredWidth: 244
                    Layout.fillHeight: true
                    color: dialog.sidebarSurface

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.space["3"]
                        anchors.rightMargin: Theme.space["3"]
                        anchors.topMargin: Theme.space["3"]
                        anchors.bottomMargin: Theme.space["3"]
                        spacing: Theme.space["2"]

                        RowLayout {
                            Layout.fillWidth: true
                            Label {
                                text: "环境"
                                color: dialog.textMuted
                                font.pixelSize: Theme.fontSize.caption
                                font.weight: Font.DemiBold
                                Layout.fillWidth: true
                            }
                            UiIconButton {
                                dark: dialog.dark
                                controlSize: 28
                                iconSize: 14
                                iconName: "mdi6.plus"
                                tooltip: "新建环境"
                                onClicked: dialog.addEnvironment()
                            }
                        }

                        Flickable {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            contentHeight: envList.implicitHeight

                            ColumnLayout {
                                id: envList
                                width: parent.width
                                spacing: Theme.space["1.5"]

                                Repeater {
                                    model: dialog.draftEnvironments
                                    delegate: Rectangle {
                                        id: envItem
                                        required property int index
                                        required property var modelData
                                        property bool active: index === dialog.selectedIndex

                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 50
                                        radius: Theme.radii.md
                                        color: active
                                            ? dialog.selectedFill
                                            : (envMouse.containsMouse ? (dialog.dark ? Qt.rgba(1, 1, 1, 0.055) : Qt.rgba(255, 255, 255, 0.72)) : "transparent")
                                        border.width: active ? 1 : 0
                                        border.color: active ? Qt.rgba(Theme.token("color-primary-active", dialog.dark).r, Theme.token("color-primary-active", dialog.dark).g, Theme.token("color-primary-active", dialog.dark).b, dialog.dark ? 0.26 : 0.18) : "transparent"
                                        antialiasing: true

                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: Theme.space["2.5"]
                                            anchors.rightMargin: Theme.space["2"]
                                            spacing: Theme.space["2"]

                                            Rectangle {
                                                Layout.preferredWidth: 26
                                                Layout.preferredHeight: 26
                                                radius: 8
                                                color: envItem.active ? Theme.token("color-primary-active", dialog.dark) : (dialog.dark ? Qt.rgba(1, 1, 1, 0.075) : "#FFFFFF")
                                                border.width: envItem.active ? 0 : 1
                                                border.color: dialog.hairline
                                                antialiasing: true
                                                Label {
                                                    anchors.centerIn: parent
                                                    text: (modelData.name || "环").slice(0, 1)
                                                    color: envItem.active ? "white" : dialog.textMuted
                                                    font.pixelSize: Theme.fontSize.caption
                                                    font.weight: Font.DemiBold
                                                }
                                            }

                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 0
                                                Label {
                                                    Layout.fillWidth: true
                                                    text: modelData.name || "未命名环境"
                                                    color: dialog.textMain
                                                    font.pixelSize: Theme.fontSize.body
                                                    font.weight: envItem.active ? Font.DemiBold : Font.Normal
                                                    elide: Text.ElideRight
                                                }
                                                Label {
                                                    Layout.fillWidth: true
                                                    text: modelData.baseUrl || "未设置 Base URL"
                                                    color: dialog.textSubtle
                                                    font.pixelSize: Theme.fontSize.caption
                                                    elide: Text.ElideMiddle
                                                }
                                            }
                                        }

                                        MouseArea {
                                            id: envMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                dialog.commitActiveField()
                                                dialog.commitActiveEditor()
                                                dialog.selectedIndex = index
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: dialog.hairline }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 0

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 60
                        color: dialog.toolbarSurface
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.space["4"]
                            anchors.rightMargin: Theme.space["3"]
                            spacing: Theme.space["2"]

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 0
                                Label {
                                    Layout.fillWidth: true
                                    text: dialog.currentEnvironment().name || "环境"
                                    color: dialog.textMain
                                    font.pixelSize: 15
                                    font.weight: Font.DemiBold
                                    elide: Text.ElideRight
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text: dialog.currentEnvironment().baseUrl || "未设置 Base URL"
                                    color: dialog.textSubtle
                                    font.pixelSize: Theme.fontSize.caption
                                    elide: Text.ElideMiddle
                                }
                            }

                            UiButton {
                                text: "复制"
                                dark: dialog.dark
                                iconName: "mdi6.content-copy"
                                iconSize: 14
                                variant: "secondary"
                                controlRadius: 9
                                implicitWidth: 72
                                implicitHeight: 28
                                onClicked: dialog.duplicateCurrentEnvironment()
                            }

                            UiButton {
                                text: "删除"
                                dark: dialog.dark
                                iconName: "mdi6.trash-can-outline"
                                iconSize: 14
                                variant: "secondary"
                                danger: true
                                controlRadius: 9
                                implicitWidth: 64
                                implicitHeight: 28
                                onClicked: dialog.deleteCurrentEnvironment()
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: dialog.hairline }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.leftMargin: Theme.space["4"]
                        Layout.rightMargin: Theme.space["4"]
                        Layout.topMargin: Theme.space["3"]
                        Layout.bottomMargin: Theme.space["3"]
                        spacing: Theme.space["2.5"]

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            columnSpacing: Theme.space["3"]
                            rowSpacing: Theme.space["1.5"]

                            Label {
                                text: "名称"
                                color: dialog.textMuted
                                font.pixelSize: Theme.fontSize.caption
                                Layout.alignment: Qt.AlignVCenter
                            }
                            UiTextField {
                                id: envNameInput
                                Layout.fillWidth: true
                                Layout.preferredHeight: 28
                                dark: dialog.dark
                                text: dialog.currentEnvironment().name || ""
                                placeholderText: "未命名环境"
                                onTextEdited: {
                                    dialog.updateCurrentEnvironment("name", text.trim())
                                    dialog.scheduleAutoSave()
                                }
                                onEditingFinished: dialog.updateCurrentEnvironment("name", text.trim())
                                onActiveFocusChanged: {
                                    if (activeFocus)
                                        dialog.setActiveField("name", envNameInput)
                                    else
                                        dialog.clearActiveField(envNameInput)
                                }
                            }

                            Label {
                                text: "Base URL"
                                color: dialog.textMuted
                                font.pixelSize: Theme.fontSize.caption
                                Layout.alignment: Qt.AlignVCenter
                            }
                            UiTextField {
                                id: envBaseUrlInput
                                Layout.fillWidth: true
                                Layout.preferredHeight: 28
                                dark: dialog.dark
                                text: dialog.currentEnvironment().baseUrl || ""
                                placeholderText: "http://127.0.0.1:8000"
                                onTextEdited: {
                                    dialog.updateCurrentEnvironment("baseUrl", text.trim())
                                    dialog.scheduleAutoSave()
                                }
                                onEditingFinished: dialog.updateCurrentEnvironment("baseUrl", text.trim())
                                onActiveFocusChanged: {
                                    if (activeFocus)
                                        dialog.setActiveField("baseUrl", envBaseUrlInput)
                                    else
                                        dialog.clearActiveField(envBaseUrlInput)
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 1
                            color: dialog.hairline
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.space["2"]

                            UiSegmentedTabs {
                                Layout.preferredWidth: Math.min(260, contentPreferredWidth)
                                Layout.preferredHeight: 32
                                dark: dialog.dark
                                tabs: dialog.detailTabs
                                counts: dialog.detailCounts()
                                currentIndex: dialog.detailTab
                                controlHeight: 28
                                minItemWidth: 92
                                showIcons: false
                                showZeroCount: true
                                textColor: dialog.textMain
                                mutedColor: dialog.textSubtle
                                onActivated: function(index) { dialog.detailTab = index }
                            }

                            Item { Layout.fillWidth: true }

                            UiButton {
                                text: (dialog.detailTabs[dialog.detailTab] || dialog.detailTabs[0]).addText
                                dark: dialog.dark
                                iconName: "mdi6.plus"
                                iconSize: 14
                                variant: "secondary"
                                controlRadius: 9
                                implicitWidth: 108
                                implicitHeight: 28
                                onClicked: dialog.addRow((dialog.detailTabs[dialog.detailTab] || dialog.detailTabs[0]).kind)
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: Theme.radii.xl
                            color: dialog.dark ? Qt.rgba(1, 1, 1, 0.035) : "#FBFCFD"
                            border.width: 1
                            border.color: dialog.hairline
                            clip: true
                            antialiasing: true

                            ColumnLayout {
                                anchors.fill: parent
                                spacing: 0

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 29
                                    color: dialog.dark ? Qt.rgba(1, 1, 1, 0.045) : "#F6F7F9"

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: Theme.space["2"]
                                        anchors.rightMargin: Theme.space["2"]
                                        spacing: Theme.space["2"]

                                        Label { text: "启用"; Layout.preferredWidth: 38; color: dialog.textSubtle; font.pixelSize: Theme.fontSize.caption; font.weight: Font.Medium }
                                        Label { text: (dialog.detailTabs[dialog.detailTab] || dialog.detailTabs[0]).keyTitle; Layout.preferredWidth: 190; color: dialog.textSubtle; font.pixelSize: Theme.fontSize.caption; font.weight: Font.Medium }
                                        Label { text: (dialog.detailTabs[dialog.detailTab] || dialog.detailTabs[0]).valueTitle; Layout.fillWidth: true; color: dialog.textSubtle; font.pixelSize: Theme.fontSize.caption; font.weight: Font.Medium }
                                        Label { text: ""; Layout.preferredWidth: 38 }
                                    }
                                }

                                Flickable {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true
                                    contentHeight: rowsColumn.implicitHeight

                                    ColumnLayout {
                                        id: rowsColumn
                                        width: parent.width
                                        spacing: 0

                                        Repeater {
                                            model: dialog.currentRows()
                                            delegate: Rectangle {
                                                required property int index
                                                required property var modelData
                                                property string kind: (dialog.detailTabs[dialog.detailTab] || dialog.detailTabs[0]).kind

                                                Layout.fillWidth: true
                                                Layout.preferredHeight: 34
                                                color: rowMouse.containsMouse ? (dialog.dark ? Qt.rgba(1, 1, 1, 0.045) : "#FFFFFF") : "transparent"

                                                RowLayout {
                                                    anchors.fill: parent
                                                    anchors.leftMargin: Theme.space["1"]
                                                    anchors.rightMargin: Theme.space["1"]
                                                    spacing: Theme.space["2"]

                                                    UiCheckBox {
                                                        dark: dialog.dark
                                                        checked: modelData.enabled !== false
                                                        Layout.preferredWidth: 40
                                                        Layout.preferredHeight: 28
                                                        onToggled: dialog.updateRow(kind, index, "enabled", checked)
                                                    }

                                                    UiTextField {
                                                        id: keyInput
                                                        dark: dialog.dark
                                                        Layout.preferredWidth: 190
                                                        Layout.preferredHeight: 28
                                                        text: modelData.key || ""
                                                        color: dialog.textMain
                                                        placeholderText: kind === "headers" ? "Authorization" : "token"
                                                        placeholderTextColor: dialog.textSubtle
                                                        font.family: Theme.fontFamily.mono
                                                        font.pixelSize: Theme.fontSize.mono
                                                        background: Rectangle {
                                                            radius: Theme.radii.sm
                                                            color: keyInput.activeFocus ? dialog.surface : "transparent"
                                                            border.width: keyInput.activeFocus ? 1 : 0
                                                            border.color: Theme.token("color-primary-active", dialog.dark)
                                                            antialiasing: true
                                                        }
                                                        onEditingFinished: dialog.updateRow(kind, index, "key", text.trim())
                                                        onActiveFocusChanged: {
                                                            if (activeFocus)
                                                                dialog.setActiveEditor(kind, index, "key", keyInput)
                                                            else
                                                                dialog.clearActiveEditor(keyInput)
                                                        }
                                                    }

                                                    UiTextField {
                                                        id: valueInput
                                                        dark: dialog.dark
                                                        Layout.fillWidth: true
                                                        Layout.preferredHeight: 28
                                                        text: modelData.value || ""
                                                        color: dialog.textMain
                                                        placeholderText: kind === "headers" ? "Bearer {{token}}" : "value"
                                                        placeholderTextColor: dialog.textSubtle
                                                        font.family: Theme.fontFamily.mono
                                                        font.pixelSize: Theme.fontSize.mono
                                                        background: Rectangle {
                                                            radius: Theme.radii.sm
                                                            color: valueInput.activeFocus ? dialog.surface : "transparent"
                                                            border.width: valueInput.activeFocus ? 1 : 0
                                                            border.color: Theme.token("color-primary-active", dialog.dark)
                                                            antialiasing: true
                                                        }
                                                        onEditingFinished: dialog.updateRow(kind, index, "value", text)
                                                        onActiveFocusChanged: {
                                                            if (activeFocus)
                                                                dialog.setActiveEditor(kind, index, "value", valueInput)
                                                            else
                                                                dialog.clearActiveEditor(valueInput)
                                                        }
                                                    }

                                                    ApiDeleteButton {
                                                        dark: dialog.dark
                                                        Layout.preferredWidth: 38
                                                        Layout.preferredHeight: 28
                                                        iconColor: dialog.textMuted
                                                        dangerColor: Theme.token("color-danger", dialog.dark)
                                                        onDeleteRequested: dialog.deleteRow(kind, index)
                                                    }
                                                }

                                                MouseArea {
                                                    id: rowMouse
                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                    acceptedButtons: Qt.NoButton
                                                }

                                                Rectangle {
                                                    anchors.left: parent.left
                                                    anchors.right: parent.right
                                                    anchors.bottom: parent.bottom
                                                    height: 1
                                                    color: dialog.dark ? Qt.rgba(1, 1, 1, 0.045) : Qt.rgba(60, 60, 67, 0.065)
                                                }
                                            }
                                        }

                                        Rectangle {
                                            visible: dialog.currentRows().length === 0
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 140
                                            color: "transparent"
                                            UiEmptyState {
                                                anchors.centerIn: parent
                                                dark: dialog.dark
                                                iconName: (dialog.detailTabs[dialog.detailTab] || dialog.detailTabs[0]).icon
                                                title: (dialog.detailTabs[dialog.detailTab] || dialog.detailTabs[0]).emptyText
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: dialog.hairline }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 52
                        Layout.leftMargin: Theme.space["4"]
                        Layout.rightMargin: Theme.space["4"]
                        spacing: Theme.space["2"]

                        UiButton {
                            text: "取消"
                            dark: dialog.dark
                            variant: "ghost"
                            controlRadius: 9
                            implicitWidth: 72
                            implicitHeight: 30
                            onClicked: dialog.close()
                        }

                        Item { Layout.fillWidth: true }

                        UiButton {
                            text: "保存并关闭"
                            dark: dialog.dark
                            variant: "secondary"
                            controlRadius: 9
                            implicitWidth: 104
                            implicitHeight: 30
                            onClicked: dialog.save(true)
                        }

                        UiButton {
                            text: "保存"
                            dark: dialog.dark
                            variant: "primary"
                            controlRadius: 9
                            implicitWidth: 80
                            implicitHeight: 30
                            onClicked: dialog.save(false)
                        }
                    }
                }
            }
        }
    }
}
