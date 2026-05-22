import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../app/ui"
import "../../app/theme"

Item {
    id: root

    readonly property bool hasSettingsVm: typeof systemSettingsVm !== "undefined" && systemSettingsVm
    readonly property bool hasApp: typeof app !== "undefined" && app
    readonly property bool hasLauncherBridge: typeof launcherBridge !== "undefined" && launcherBridge
    readonly property bool dark: hasApp ? app.theme === "dark" : false
    readonly property bool isMacos: hasApp ? app.isMacos : false
    readonly property color pageBg: Theme.token("color-bg-page", dark)
    readonly property color panelBg: Theme.token("color-bg-surface", dark)
    readonly property color subtleBg: Theme.token("color-bg-subtle", dark)
    readonly property color panelBorder: Theme.token("color-border-default", dark)
    readonly property color textMain: Theme.token("color-text-primary", dark)
    readonly property color textMuted: Theme.token("color-text-regular", dark)
    readonly property color textSubtle: Theme.token("color-text-secondary", dark)
    readonly property color warningColor: Theme.token("color-warning", dark)
    readonly property color successColor: Theme.token("color-success", dark)
    readonly property string appIndexStatus: !hasSettingsVm ? "应用索引不可用" : (systemSettingsVm.appScanRunning ? "正在后台重扫描应用" : ("已缓存应用：" + systemSettingsVm.appCount))

    property var diagnostics: ({})
    property var settingsModel: hasSettingsVm ? systemSettingsVm.settingsItems : []

    function refreshDiagnostics() {
        diagnostics = hasSettingsVm ? systemSettingsVm.diagnostics() : ({})
    }

    function settingChanged(key, value) {
        if (hasSettingsVm)
            systemSettingsVm.setSetting(key, value)
    }

    function resetSetting(key) {
        if (hasSettingsVm)
            systemSettingsVm.resetSetting(key)
    }

    Component.onCompleted: refreshDiagnostics()

    Connections {
        target: root.hasSettingsVm ? systemSettingsVm : null
        function onSettingsChanged() {
            root.settingsModel = systemSettingsVm.settingsItems
            root.refreshDiagnostics()
        }
    }

    Rectangle {
        anchors.fill: parent
        color: pageBg
    }

    UiScrollView {
        id: scrollView
        anchors.fill: parent
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        ColumnLayout {
            id: contentColumn
            width: Math.max(scrollView.availableWidth, 360)
            spacing: Theme.space["3"]
            anchors.margins: Theme.space["3"]

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: Theme.space["3"]
                Layout.rightMargin: Theme.space["3"]
                spacing: Theme.space["2"]

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Label {
                        text: "系统设置"
                        font.bold: true
                        font.pixelSize: Theme.fontSize.title
                        color: textMain
                        font.family: Theme.fontFamily.ui
                    }

                    Label {
                        text: "路径、日志、插件、热键和开发开关"
                        color: textSubtle
                        font.pixelSize: Theme.fontSize.body
                        font.family: Theme.fontFamily.ui
                    }
                }

                UiButton {
                    visible: hasSettingsVm && systemSettingsVm.restartRequired
                    dark: root.dark
                    variant: "primary"
                    iconName: "mdi6.restart"
                    text: "重启应用"
                    onClicked: {
                        if (root.hasLauncherBridge)
                            launcherBridge.restartApp()
                    }
                }
            }

            RestartNotice {
                visible: hasSettingsVm && systemSettingsVm.restartRequired
                Layout.fillWidth: true
                Layout.leftMargin: Theme.space["3"]
                Layout.rightMargin: Theme.space["3"]
                dark: root.dark
            }

            SectionPanel {
                Layout.fillWidth: true
                Layout.leftMargin: Theme.space["3"]
                Layout.rightMargin: Theme.space["3"]
                dark: root.dark
                title: "外观"
                iconName: "mdi6.palette-outline"

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space["2"]

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.space["2"]

                        ThemeOption {
                            Layout.fillWidth: true
                            dark: root.dark
                            text: "浅色"
                            selected: hasApp && app.themeMode === "light"
                            onClicked: if (hasApp) app.setTheme("light")
                        }
                        ThemeOption {
                            Layout.fillWidth: true
                            dark: root.dark
                            text: "深色"
                            selected: hasApp && app.themeMode === "dark"
                            onClicked: if (hasApp) app.setTheme("dark")
                        }
                        ThemeOption {
                            Layout.fillWidth: true
                            dark: root.dark
                            text: "跟随系统"
                            selected: hasApp && app.themeMode === "auto"
                            onClicked: if (hasApp) app.setTheme("auto")
                        }
                    }
                }
            }

            SectionPanel {
                Layout.fillWidth: true
                Layout.leftMargin: Theme.space["3"]
                Layout.rightMargin: Theme.space["3"]
                dark: root.dark
                title: "项目配置"
                subtitle: "环境变量优先生效；设置文件中的变更通常需要重启后进入运行时。"
                iconName: "mdi6.tune-variant"

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0

                    Repeater {
                        model: root.settingsModel
                        delegate: SettingRow {
                            Layout.fillWidth: true
                            dark: root.dark
                            itemData: modelData
                            onValueEdited: function(key, value) { root.settingChanged(key, value) }
                            onResetRequested: function(key) { root.resetSetting(key) }
                        }
                    }
                }
            }

            SectionPanel {
                Layout.fillWidth: true
                Layout.leftMargin: Theme.space["3"]
                Layout.rightMargin: Theme.space["3"]
                dark: root.dark
                title: "应用索引"
                iconName: "mdi6.application-cog-outline"

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space["3"]

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Label {
                            text: root.appIndexStatus
                            color: textMuted
                            font.pixelSize: Theme.fontSize.body
                            font.family: Theme.fontFamily.ui
                        }

                        Label {
                            text: "用于启动器搜索本机应用。"
                            color: textSubtle
                            font.pixelSize: Theme.fontSize.caption
                            font.family: Theme.fontFamily.ui
                        }
                    }

                    UiButton {
                        Layout.preferredWidth: 128
                        Layout.preferredHeight: 34
                        dark: root.dark
                        variant: "primary"
                        iconName: "mdi6.refresh"
                        text: hasSettingsVm && systemSettingsVm.appScanRunning ? "扫描中" : "重扫描"
                        enabled: hasSettingsVm && !systemSettingsVm.appScanRunning
                        onClicked: {
                            if (hasSettingsVm)
                                systemSettingsVm.rescanApplications()
                        }
                    }
                }
            }

            SectionPanel {
                Layout.fillWidth: true
                Layout.leftMargin: Theme.space["3"]
                Layout.rightMargin: Theme.space["3"]
                dark: root.dark
                title: "macOS 权限"
                iconName: "mdi6.shield-key-outline"
                visible: root.isMacos

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space["3"]

                    Label {
                        Layout.fillWidth: true
                        text: hasSettingsVm ? systemSettingsVm.accessibilityStatusText : "辅助功能权限：未知"
                        color: textMuted
                        font.pixelSize: Theme.fontSize.body
                        font.family: Theme.fontFamily.ui
                    }

                    UiButton {
                        Layout.preferredWidth: 128
                        Layout.preferredHeight: 34
                        dark: root.dark
                        variant: "primary"
                        text: hasSettingsVm && systemSettingsVm.accessibilityAuthorized ? "已授权" : "去授权"
                        enabled: hasSettingsVm
                        onClicked: {
                            if (hasSettingsVm)
                                systemSettingsVm.openAccessibilitySettings()
                        }
                    }
                }
            }

            SectionPanel {
                Layout.fillWidth: true
                Layout.leftMargin: Theme.space["3"]
                Layout.rightMargin: Theme.space["3"]
                Layout.bottomMargin: Theme.space["3"]
                dark: root.dark
                title: "开发诊断"
                iconName: "mdi6.stethoscope"

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space["1.5"]

                    DiagnosticLine { dark: root.dark; label: "平台"; value: diagnostics.platform || "" }
                    DiagnosticLine { dark: root.dark; label: "数据目录"; value: diagnostics.dataDir || "" }
                    DiagnosticLine { dark: root.dark; label: "日志目录"; value: diagnostics.logDir || "" }
                    DiagnosticLine { dark: root.dark; label: "设置文件"; value: diagnostics.settingsFile || "" }
                    DiagnosticLine { dark: root.dark; label: "插件目录"; value: diagnostics.pluginDirs || "" }
                    DiagnosticLine { dark: root.dark; label: "插件数量"; value: "" + (diagnostics.pluginCount || 0) }
                    DiagnosticLine { dark: root.dark; label: "后台插件"; value: diagnostics.backgroundPlugins || "无" }
                }
            }
        }
    }

    component SectionPanel: Rectangle {
        id: panel
        property bool dark: false
        property string title: ""
        property string subtitle: ""
        property string iconName: ""
        default property alias panelContent: body.data

        implicitHeight: sectionColumn.implicitHeight + Theme.space["6"]
        radius: Theme.radii.md
        color: Theme.token("color-bg-surface", dark)
        border.width: 1
        border.color: Theme.token("color-border-default", dark)

        ColumnLayout {
            id: sectionColumn
            anchors.fill: parent
            anchors.margins: Theme.space["3"]
            spacing: Theme.space["2"]

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.space["2"]

                Rectangle {
                    Layout.preferredWidth: 34
                    Layout.preferredHeight: 34
                    radius: Theme.radii.md
                    color: Theme.token("color-primary-bg", panel.dark)

                    UiIcon {
                        anchors.centerIn: parent
                        width: 18
                        height: 18
                        name: panel.iconName
                        color: Theme.token("color-primary", panel.dark)
                        iconSize: 18
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 1

                    Label {
                        text: panel.title
                        font.bold: true
                        font.pixelSize: Theme.fontSize.heading
                        color: Theme.token("color-text-primary", panel.dark)
                        font.family: Theme.fontFamily.ui
                    }

                    Label {
                        visible: panel.subtitle.length > 0
                        text: panel.subtitle
                        color: Theme.token("color-text-secondary", panel.dark)
                        font.pixelSize: Theme.fontSize.caption
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                        font.family: Theme.fontFamily.ui
                    }
                }
            }

            ColumnLayout {
                id: body
                Layout.fillWidth: true
                spacing: Theme.space["2"]
            }
        }
    }

    component RestartNotice: Rectangle {
        id: notice
        property bool dark: false

        implicitHeight: noticeRow.implicitHeight + Theme.space["3"]
        radius: Theme.radii.md
        color: Qt.rgba(Theme.token("color-warning", dark).r, Theme.token("color-warning", dark).g, Theme.token("color-warning", dark).b, dark ? 0.18 : 0.12)
        border.width: 1
        border.color: Qt.rgba(Theme.token("color-warning", dark).r, Theme.token("color-warning", dark).g, Theme.token("color-warning", dark).b, 0.35)

        RowLayout {
            id: noticeRow
            anchors.fill: parent
            anchors.margins: Theme.space["2"]
            spacing: Theme.space["2"]

            UiIcon {
                Layout.preferredWidth: 18
                Layout.preferredHeight: 18
                name: "mdi6.alert-circle-outline"
                color: Theme.token("color-warning", notice.dark)
                iconSize: 18
            }

            Label {
                Layout.fillWidth: true
                text: "部分项目已保存到设置文件，但当前进程仍在使用旧值。重启应用后生效。"
                color: Theme.token("color-text-primary", notice.dark)
                font.pixelSize: Theme.fontSize.body
                wrapMode: Text.Wrap
                font.family: Theme.fontFamily.ui
            }
        }
    }

    component ThemeOption: Rectangle {
        id: option
        property bool dark: false
        property bool selected: false
        property string text: ""
        signal clicked()

        Layout.preferredHeight: 34
        radius: Theme.radii.md
        color: selected ? Theme.token("color-primary-bg", dark) : Theme.token("color-bg-subtle-2", dark)
        border.width: 1
        border.color: selected ? Theme.token("color-primary-active", dark) : Theme.token("color-border-default", dark)

        Label {
            anchors.centerIn: parent
            text: option.text
            color: option.selected ? Theme.token("color-primary-active", option.dark) : Theme.token("color-text-regular", option.dark)
            font.bold: option.selected
            font.pixelSize: Theme.fontSize.body
            font.family: Theme.fontFamily.ui
        }

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: option.clicked()
        }
    }

    component SettingRow: Rectangle {
        id: row
        property bool dark: false
        property var itemData: ({})
        signal valueEdited(string key, var value)
        signal resetRequested(string key)

        readonly property string kind: itemData.kind || "text"
        readonly property bool envLocked: itemData.source === "env"
        readonly property bool pending: itemData.pending === true
        readonly property color lineColor: Theme.token("color-border-default", dark)
        readonly property color rowBg: pending
            ? Qt.rgba(Theme.token("color-warning", dark).r, Theme.token("color-warning", dark).g, Theme.token("color-warning", dark).b, dark ? 0.12 : 0.07)
            : "transparent"

        Layout.fillWidth: true
        implicitHeight: rowContent.implicitHeight + Theme.space["4"]
        color: rowBg

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 1
            color: row.lineColor
            opacity: 0.7
        }

        RowLayout {
            id: rowContent
            anchors.fill: parent
            anchors.margins: Theme.space["2"]
            spacing: Theme.space["3"]

            ColumnLayout {
                Layout.preferredWidth: 210
                Layout.maximumWidth: 240
                Layout.alignment: Qt.AlignTop
                spacing: 3

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space["1"]

                    Label {
                        Layout.fillWidth: true
                        text: itemData.label || ""
                        color: Theme.token("color-text-primary", row.dark)
                        font.bold: true
                        font.pixelSize: Theme.fontSize.body
                        elide: Text.ElideRight
                        font.family: Theme.fontFamily.ui
                    }

                    SourceBadge {
                        dark: row.dark
                        text: itemData.sourceText || ""
                        pending: row.pending
                    }
                }

                Label {
                    Layout.fillWidth: true
                    text: itemData.description || ""
                    visible: text.length > 0
                    color: Theme.token("color-text-secondary", row.dark)
                    font.pixelSize: Theme.fontSize.caption
                    wrapMode: Text.Wrap
                    font.family: Theme.fontFamily.ui
                }

                Label {
                    Layout.fillWidth: true
                    text: itemData.env ? ("环境变量：" + (itemData.activeEnv || itemData.env)) : "设置文件项"
                    color: Theme.token("color-text-secondary", row.dark)
                    font.pixelSize: Theme.fontSize.caption
                    elide: Text.ElideMiddle
                    font.family: Theme.fontFamily.ui
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.space["1"]

                Loader {
                    id: editorLoader
                    Layout.fillWidth: true
                    sourceComponent: {
                        if (row.kind === "bool")
                            return boolEditor
                        if (row.kind === "choice")
                            return choiceEditor
                        if (row.kind === "int")
                            return intEditor
                        return textEditor
                    }
                }

                Label {
                    Layout.fillWidth: true
                    text: row.pending ? ("当前生效值：" + itemData.effectiveValue) : ""
                    visible: row.pending
                    color: Theme.token("color-warning", row.dark)
                    font.pixelSize: Theme.fontSize.caption
                    elide: Text.ElideMiddle
                    font.family: Theme.fontFamily.ui
                }
            }

            UiButton {
                Layout.preferredWidth: 86
                Layout.alignment: Qt.AlignTop
                dark: row.dark
                variant: "ghost"
                text: "重置"
                enabled: itemData.source === "settings"
                onClicked: row.resetRequested(itemData.key)
            }
        }

        Component {
            id: boolEditor
            RowLayout {
                spacing: Theme.space["2"]

                UiSwitch {
                    dark: row.dark
                    checked: itemData.value === true
                    switchEnabled: !row.envLocked
                    onToggled: function(checked) { row.valueEdited(itemData.key, checked) }
                }

                Label {
                    Layout.fillWidth: true
                    text: row.envLocked ? ("由环境变量控制：" + itemData.effectiveValue) : (itemData.value === true ? "已开启" : "已关闭")
                    color: Theme.token("color-text-regular", row.dark)
                    font.pixelSize: Theme.fontSize.body
                    font.family: Theme.fontFamily.ui
                }
            }
        }

        Component {
            id: choiceEditor
            RowLayout {
                spacing: Theme.space["2"]

                UiComboBox {
                    id: combo
                    Layout.preferredWidth: 180
                    dark: row.dark
                    enabled: !row.envLocked
                    model: itemData.options || []
                    currentIndex: Math.max(0, (itemData.options || []).indexOf("" + itemData.value))
                    onActivated: function(index) { row.valueEdited(itemData.key, combo.textAt(index)) }
                }

                Label {
                    Layout.fillWidth: true
                    text: row.envLocked ? ("由环境变量控制：" + itemData.effectiveValue) : ""
                    visible: text.length > 0
                    color: Theme.token("color-text-secondary", row.dark)
                    font.pixelSize: Theme.fontSize.caption
                    elide: Text.ElideMiddle
                    font.family: Theme.fontFamily.ui
                }
            }
        }

        Component {
            id: intEditor
            RowLayout {
                spacing: Theme.space["2"]

                UiTextField {
                    id: input
                    Layout.preferredWidth: 150
                    dark: row.dark
                    enabled: !row.envLocked
                    text: "" + itemData.value
                    validator: IntValidator {
                        bottom: itemData.minimum || 0
                        top: itemData.maximum || 2147483647
                    }
                    onEditingFinished: row.valueEdited(itemData.key, text)
                    Keys.onReturnPressed: row.valueEdited(itemData.key, text)
                    Keys.onEnterPressed: row.valueEdited(itemData.key, text)
                }

                Label {
                    Layout.fillWidth: true
                    text: row.envLocked ? ("由环境变量控制：" + itemData.effectiveValue) : ("范围：" + itemData.minimum + " - " + itemData.maximum)
                    color: Theme.token("color-text-secondary", row.dark)
                    font.pixelSize: Theme.fontSize.caption
                    elide: Text.ElideMiddle
                    font.family: Theme.fontFamily.ui
                }
            }
        }

        Component {
            id: textEditor
            RowLayout {
                spacing: Theme.space["2"]

                UiTextField {
                    id: input
                    Layout.fillWidth: true
                    dark: row.dark
                    enabled: !row.envLocked
                    text: "" + itemData.value
                    placeholderText: "" + itemData.defaultValue
                    onEditingFinished: row.valueEdited(itemData.key, text)
                    Keys.onReturnPressed: row.valueEdited(itemData.key, text)
                    Keys.onEnterPressed: row.valueEdited(itemData.key, text)
                }

                UiButton {
                    visible: row.kind === "path"
                    dark: row.dark
                    variant: "ghost"
                    iconName: "mdi6.folder-open-outline"
                    text: "打开"
                    enabled: root.hasSettingsVm
                    onClicked: systemSettingsVm.openPath("" + itemData.effectiveValue)
                }
            }
        }
    }

    component SourceBadge: Rectangle {
        id: badge
        property bool dark: false
        property bool pending: false
        property string text: ""

        implicitWidth: label.implicitWidth + Theme.space["2"]
        implicitHeight: 20
        radius: Theme.radii.sm
        color: pending
            ? Qt.rgba(Theme.token("color-warning", dark).r, Theme.token("color-warning", dark).g, Theme.token("color-warning", dark).b, dark ? 0.20 : 0.14)
            : Theme.token("color-bg-subtle", dark)
        border.width: 1
        border.color: pending ? Theme.token("color-warning", dark) : Theme.token("color-border-default", dark)

        Label {
            id: label
            anchors.centerIn: parent
            text: badge.pending ? "待重启" : badge.text
            color: badge.pending ? Theme.token("color-warning", badge.dark) : Theme.token("color-text-secondary", badge.dark)
            font.pixelSize: Theme.fontSize.caption
            font.family: Theme.fontFamily.ui
        }
    }

    component DiagnosticLine: RowLayout {
        id: diagnosticLine
        property bool dark: false
        property string label: ""
        property string value: ""

        Layout.fillWidth: true
        spacing: Theme.space["2"]

        Label {
            Layout.preferredWidth: 74
            text: diagnosticLine.label
            color: Theme.token("color-text-secondary", diagnosticLine.dark)
            font.pixelSize: Theme.fontSize.caption
            horizontalAlignment: Text.AlignRight
            font.family: Theme.fontFamily.ui
        }

        Label {
            Layout.fillWidth: true
            text: diagnosticLine.value
            color: Theme.token("color-text-regular", diagnosticLine.dark)
            font.pixelSize: Theme.fontSize.caption
            elide: Text.ElideMiddle
            font.family: Theme.fontFamily.ui
        }
    }
}
