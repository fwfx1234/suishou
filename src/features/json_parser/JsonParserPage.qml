import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../app/ui"
import "../../app/theme"

Item {
    id: root
    readonly property bool dark: app.theme === "dark"
    readonly property color panelBg: Theme.token("color-bg-surface", dark)
    readonly property color subtleBg: Theme.token("color-bg-subtle", dark)
    readonly property color statusBg: Theme.token("color-status-bar-bg", dark)
    readonly property color panelBorder: Theme.token("color-border-default", dark)
    readonly property color textMain: Theme.token("color-text-primary", dark)
    readonly property color textMuted: Theme.token("color-text-regular", dark)
    readonly property color textSubtle: Theme.token("color-text-secondary", dark)
    readonly property color successColor: Theme.token("color-success", dark)
    readonly property color dangerColor: Theme.token("color-danger", dark)

    property string lastMode: "format"
    property string statusText: "就绪"
    property color statusColor: textMuted
    property string statsText: ""
    property string errorLocText: ""

    function setStatus(text, kind) {
        statusText = text
        if (kind === "success") statusColor = successColor
        else if (kind === "error") statusColor = dangerColor
        else statusColor = textMuted
    }

    function runMode(mode) {
        lastMode = mode
        if (mode === "format") jsonParserVm.formatJson(input.text)
        else if (mode === "compress") jsonParserVm.compressJson(input.text)
        else if (mode === "query") jsonParserVm.queryJson(input.text, query.text)
    }

    Component.onCompleted: {
        input.text = jsonParserVm.initialText()
        if (input.text.length > 0)
            runMode("format")
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space["3"]
        spacing: Theme.space["2"]

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space["2"]
            Label {
                text: "JSON 解析"
                font.bold: true
                font.pixelSize: Theme.fontSize.title
                color: textMain
                font.family: Theme.fontFamily.ui
            }
            Item { Layout.fillWidth: true }
        }

        Flow {
            Layout.fillWidth: true
            Layout.preferredHeight: implicitHeight
            spacing: Theme.space["2"]

            UiButton { text: "格式化"; dark: root.dark; variant: lastMode === "format" ? "primary" : "secondary"; onClicked: runMode("format") }
            UiButton { text: "压缩"; dark: root.dark; variant: lastMode === "compress" ? "primary" : "secondary"; onClicked: runMode("compress") }
            UiButton { text: "执行查询"; dark: root.dark; variant: lastMode === "query" ? "primary" : "secondary"; onClicked: runMode("query") }
            UiButton { text: "复制输出"; dark: root.dark; variant: "ghost"; onClicked: jsonParserVm.copyText(output.text) }
            UiButton { text: "从剪贴板填充"; dark: root.dark; variant: "ghost"; onClicked: jsonParserVm.fillFromClipboard() }
            UiButton {
                text: "清空"
                dark: root.dark
                variant: "ghost"
                onClicked: {
                    input.text = ""
                    query.text = ""
                    output.text = ""
                    errorLocText = ""
                    statsText = ""
                    setStatus("就绪", "info")
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Label { text: "JSONPath"; color: textMuted; font.pixelSize: Theme.fontSize.caption }
            UiTextField {
                id: query
                dark: root.dark
                Layout.fillWidth: true
                placeholderText: "$.foo.bar  /  $[0].name"
                onAccepted: runMode("query")
            }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal
            handle: Rectangle {
                implicitWidth: 6
                color: "transparent"
            }

            ColumnLayout {
                SplitView.preferredWidth: parent.width * 0.5
                SplitView.minimumWidth: 240
                spacing: Theme.space["1"]

                Label { text: "输入"; color: textSubtle; font.pixelSize: Theme.fontSize.caption }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: panelBg
                    radius: Theme.radii.md
                    border.color: panelBorder
                    border.width: 1

                    JsonEditorPane {
                        id: input
                        anchors.fill: parent
                        backgroundColor: panelBg
                        placeholderText: "粘贴或输入 JSON..."
                    }
                }
            }

            ColumnLayout {
                SplitView.preferredWidth: parent.width * 0.5
                SplitView.minimumWidth: 240
                spacing: Theme.space["1"]

                Label {
                    text: lastMode === "compress" ? "输出 (压缩)" : lastMode === "query" ? "输出 (查询结果)" : "输出 (格式化)"
                    color: textSubtle
                    font.pixelSize: Theme.fontSize.caption
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: subtleBg
                    radius: Theme.radii.md
                    border.color: panelBorder
                    border.width: 1

                    JsonEditorPane {
                        id: output
                        anchors.fill: parent
                        backgroundColor: subtleBg
                        readOnly: true
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.space["3"] * 2 + Theme.space["1"]
            color: statusBg
            radius: Theme.radii.sm

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.space["2"]
                anchors.rightMargin: Theme.space["2"]
                spacing: Theme.space["2"]

                Label {
                    text: statusText
                    color: statusColor
                    font.pixelSize: Theme.fontSize.caption
                    elide: Text.ElideMiddle
                    Layout.fillWidth: true
                }

                Label {
                    text: errorLocText
                    color: dangerColor
                    visible: errorLocText.length > 0
                    font.pixelSize: Theme.fontSize.caption
                    font.family: Theme.fontFamily.mono
                }

                Label {
                    text: statsText
                    color: textSubtle
                    font.pixelSize: Theme.fontSize.caption
                    font.family: Theme.fontFamily.mono
                }
            }
        }
    }

    component JsonEditorPane: Rectangle {
        id: pane

        property alias text: editor.text
        property string placeholderText: ""
        property bool readOnly: false
        property color backgroundColor: panelBg

        color: backgroundColor
        clip: true

        Flickable {
            id: flick
            anchors.fill: parent
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            contentWidth: Math.max(width, editor.paintedWidth + editor.leftPadding + editor.rightPadding)
            contentHeight: Math.max(height, editor.paintedHeight + editor.topPadding + editor.bottomPadding)

            TextEdit {
                id: editor
                width: Math.max(flick.width, paintedWidth + leftPadding + rightPadding)
                height: Math.max(flick.height, paintedHeight + topPadding + bottomPadding)
                leftPadding: Theme.space["2"]
                rightPadding: Theme.space["2"]
                topPadding: Theme.space["2"]
                bottomPadding: Theme.space["2"]
                wrapMode: TextEdit.NoWrap
                readOnly: pane.readOnly
                selectByMouse: true
                persistentSelection: true
                textFormat: TextEdit.PlainText
                color: textMain
                font.family: Theme.fontFamily.mono
                font.pixelSize: Theme.fontSize.mono
            }

            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AsNeeded
            }

            ScrollBar.horizontal: ScrollBar {
                policy: ScrollBar.AsNeeded
            }
        }

        Label {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.margins: Theme.space["2"]
            visible: !pane.readOnly && editor.text.length === 0
            text: pane.placeholderText
            color: textSubtle
            font.family: Theme.fontFamily.mono
            font.pixelSize: Theme.fontSize.mono
        }
    }

    Connections {
        target: jsonParserVm
        function onResultUpdated(payload) {
            if (payload.error) {
                output.text = ""
                statsText = ""
                errorLocText = payload.errorLine > 0
                    ? ("L" + payload.errorLine + ":C" + payload.errorColumn)
                    : ""
                setStatus(payload.error, "error")
            } else {
                output.text = payload.output
                errorLocText = ""
                if (payload.output.length > 0) {
                    var labelKind = payload.kind || "-"
                    statsText = labelKind + " · 字符 " + payload.charCount
                        + " · 行 " + payload.lineCount
                        + (payload.size > 0 ? " · 元素 " + payload.size : "")
                        + (payload.depth > 0 ? " · 深度 " + payload.depth : "")
                } else {
                    statsText = ""
                }
                var modeLabel = payload.mode === "compress" ? "压缩完成"
                    : payload.mode === "query" ? "查询完成"
                    : "格式化完成"
                setStatus(modeLabel, payload.output.length > 0 ? "success" : "info")
            }
        }
        function onJsonCopied(ok, message) {
            setStatus(message, ok ? "success" : "error")
        }
        function onStatusMessage(message, kind) {
            setStatus(message, kind)
        }
        function onInputTextChanged(text) {
            if (input.text !== text)
                input.text = text
        }
        function onInputFilled(text) {
            input.text = text
            runMode("format")
        }
    }
}
