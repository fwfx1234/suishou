import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import QtWebEngine
import QtWebChannel
import "../../app/ui"
import "../../app/theme"

Item {
    id: root

    property var selectedProfile: null
    property var selectedRemoteItems: []
    property var editingProfile: ({})
    property var contextItem: null
    property var contextProfile: null
    property var pendingEditedFile: ({})
    property string lastToastMessage: ""
    readonly property bool dark: app.theme === "dark"
    readonly property bool connected: (remoteFilesVm.connectionState.status || "") === "connected"
    readonly property bool connecting: (remoteFilesVm.connectionState.status || "") === "connecting"
    readonly property bool errored: (remoteFilesVm.connectionState.status || "") === "error"
    readonly property bool sftpConnected: connected && (remoteFilesVm.connectionState.protocol || "") === "sftp"
    readonly property color pageBg: dark ? "#0E1117" : "#F2F3F7"
    readonly property color sidebarBg: dark ? "#1B2029" : "#E4E7EE"
    readonly property color surface: dark ? "#1F242E" : "#FFFFFF"
    readonly property color surfaceSubtle: dark ? "#252B36" : "#F5F6FA"
    readonly property color surfaceElevated: dark ? "#2A303C" : "#FFFFFF"
    readonly property color toolbarBg: dark ? "#1B2029" : "#F8F9FC"
    readonly property color border: dark ? "#363D4B" : "#D6D8E1"
    readonly property color separator: dark ? "#2F3644" : "#E0E2EA"
    readonly property color rowHover: dark ? "#2A3140" : "#E9EBF1"
    readonly property color selectedBg: "#0A84FF"
    readonly property color selectedSoftBg: dark ? "#1B3D6B" : "#D6E7FF"
    readonly property color textMain: dark ? "#FAFBFC" : "#15171B"
    readonly property color textMuted: dark ? "#B8BDC7" : "#5A5E66"
    readonly property color textFaint: dark ? "#8A909C" : "#878A91"
    readonly property color danger: "#FF453A"
    readonly property color success: "#30D158"
    readonly property color warning: "#FFD60A"
    readonly property color tagBg: dark ? "#33394A" : "#E3E5EE"
    readonly property color tagText: dark ? "#C7CBD3" : "#4B4E55"

    readonly property var sessionList: remoteFilesVm.sessions || []
    readonly property var sftpSessionList: {
        var out = []
        var sessions = sessionList
        for (var i = 0; i < sessions.length; i++) {
            if ((sessions[i].protocol || "") === "sftp")
                out.push(sessions[i])
        }
        return out
    }
    readonly property string activeProtocol: (remoteFilesVm.connectionState.protocol || "").toLowerCase()
    readonly property string rightPaneMode: {
        if (activeProtocol === "ftp" || activeProtocol === "ftps") return "ftp"
        if (activeProtocol === "sftp") return "sftp"
        return "empty"
    }

    function statusColorForId(profileId) {
        var sessions = sessionList
        for (var i = 0; i < sessions.length; i++) {
            if (sessions[i].profileId !== profileId) continue
            var status = sessions[i].status || ""
            if (status === "connected") return success
            if (status === "connecting") return warning
            if (status === "error") return danger
            return textFaint
        }
        return "transparent"
    }
    function sessionExists(profileId) {
        var sessions = sessionList
        for (var i = 0; i < sessions.length; i++) {
            if (sessions[i].profileId === profileId) return true
        }
        return false
    }

    function emptyProfile() {
        return {
            id: "",
            name: "",
            protocol: "sftp",
            host: "",
            port: 22,
            username: "",
            password: "",
            remoteRoot: "",
            localRoot: "",
            encoding: "utf-8",
            passiveMode: true,
            authKind: "password",
            privateKeyPath: "",
            privateKeyPassphrase: "",
            connectTimeout: 15,
            jumpEnabled: false,
            jumpHost: "",
            jumpPort: 22,
            jumpUsername: "",
            jumpPassword: "",
            jumpPrivateKeyPath: "",
            jumpPrivateKeyPassphrase: ""
        }
    }

    function copyProfile(source) {
        var profile = emptyProfile()
        if (!source)
            return profile
        for (var key in profile) {
            if (source[key] !== undefined)
                profile[key] = source[key]
        }
        if (source.rawName !== undefined)
            profile.name = source.rawName
        return profile
    }

    function resetProfileDialogFields() {
        var p = editingProfile || {}
        var defaultPort = (p.protocol || "sftp") === "sftp" ? 22 : 21
        nameField.text = p.name || ""
        protocolBox.currentIndex = (p.protocol || "sftp") === "ftp"
            ? 1
            : (p.protocol || "sftp") === "ftps" ? 2 : 0
        hostField.text = p.host || ""
        portField.text = String(p.port || defaultPort)
        usernameField.text = p.username || ""
        passwordField.text = p.password || ""
        authBox.currentIndex = (p.authKind || "password") === "private_key"
            ? 1
            : (p.authKind || "password") === "agent" ? 2 : 0
        keyPathField.text = p.privateKeyPath || ""
        keyPassField.text = p.privateKeyPassphrase || ""
        remoteRootField.text = p.remoteRoot || ""
        localRootField.text = p.localRoot || ""
        encodingField.text = p.encoding || "utf-8"
        timeoutField.text = String(p.connectTimeout || 15)
        passiveSwitch.checked = p.passiveMode !== false
        jumpSwitch.checked = p.jumpEnabled || false
        jumpHostField.text = p.jumpHost || ""
        jumpPortField.text = String(p.jumpPort || 22)
        jumpUserField.text = p.jumpUsername || ""
        jumpPasswordField.text = p.jumpPassword || ""
        jumpKeyField.text = p.jumpPrivateKeyPath || ""
        jumpKeyPassField.text = p.jumpPrivateKeyPassphrase || ""
    }

    function profileSubtitle(profile) {
        if (!profile)
            return "未选择"
        var user = profile.username ? profile.username + "@" : ""
        var host = profile.host || ""
        var port = profile.port ? ":" + profile.port : ""
        return user + host + port
    }

    function selectedProfileName() {
        if (selectedProfile)
            return selectedProfile.name || "未命名连接"
        if (connecting)
            return "连接中"
        if (connected)
            return (remoteFilesVm.connectionState.protocol || "").toUpperCase() + " " + (remoteFilesVm.connectionState.host || "")
        return "未选择连接"
    }

    function selectedProfileSubtitle() {
        if (selectedProfile)
            return profileSubtitle(selectedProfile)
        if (remoteFilesVm.connectionState.host)
            return remoteFilesVm.connectionState.host
        return "SFTP / FTP / FTPS"
    }

    function statusColor() {
        if (connected)
            return success
        if (connecting)
            return warning
        if (errored)
            return danger
        return textFaint
    }

    function statusText() {
        if (remoteFilesVm.statusMessage)
            return remoteFilesVm.statusMessage
        if (connected)
            return "已连接"
        if (connecting)
            return "连接中"
        if (errored)
            return "连接失败"
        return "未连接"
    }

    function formatSize(size) {
        var value = Number(size || 0)
        if (value >= 1024 * 1024 * 1024)
            return (value / 1024 / 1024 / 1024).toFixed(1) + " GB"
        if (value >= 1024 * 1024)
            return (value / 1024 / 1024).toFixed(1) + " MB"
        if (value >= 1024)
            return (value / 1024).toFixed(1) + " KB"
        return value + " B"
    }

    function formatModifiedTime(epoch) {
        var value = Number(epoch || 0)
        if (value <= 0)
            return ""
        var timestamp = value > 9999999999 ? value : value * 1000
        var date = new Date(timestamp)
        if (isNaN(date.getTime()))
            return ""
        function pad(n) { return n < 10 ? "0" + n : String(n) }
        return date.getFullYear() + "-" + pad(date.getMonth() + 1) + "-" + pad(date.getDate()) + " " + pad(date.getHours()) + ":" + pad(date.getMinutes())
    }

    function showStatusToast(message) {
        var text = String(message || "")
        if (text.length === 0 || text === lastToastMessage)
            return
        lastToastMessage = text
        toast.show(text)
    }

    function shortenPath(path, maxLen) {
        var text = String(path || "")
        if (text.length <= maxLen)
            return text
        return "…" + text.substring(text.length - maxLen + 1)
    }

    function ensureSelectedProfile() {
        var profiles = remoteFilesVm.profiles || []
        if (profiles.length === 0) {
            selectedProfile = null
            return
        }
        if (selectedProfile) {
            for (var i = 0; i < profiles.length; i++) {
                if (profiles[i].id === selectedProfile.id) {
                    selectedProfile = profiles[i]
                    return
                }
            }
        }
        selectedProfile = profiles[0]
    }

    function openProfileEditor(source) {
        editingProfile = source ? copyProfile(source) : emptyProfile()
        profileDialog.showAdvanced = false
        profileDialog.open()
    }

    function duplicateProfile(source) {
        if (!source)
            return
        var copy = copyProfile(source)
        copy.id = ""
        copy.name = (source.name || "未命名连接") + " 副本"
        editingProfile = copy
        profileDialog.showAdvanced = false
        profileDialog.open()
    }

    Component.onCompleted: ensureSelectedProfile()

    Connections {
        target: remoteFilesVm
        function onProfilesChanged() { root.ensureSelectedProfile() }
        function onStatusMessageChanged() {
            var message = remoteFilesVm.statusMessage || ""
            if (message.indexOf("上传") >= 0 || message.indexOf("传输") >= 0 || message.indexOf("失败") >= 0)
                root.showStatusToast(message)
        }
        function onFtpLogCopied(ok, message) {
            root.showStatusToast(message || (ok ? "日志已复制" : "复制失败"))
        }
        function onHostKeyPromptRequested(info) {
            hostKeyDialog.profileId = info.profileId || ""
            hostKeyDialog.host = info.host || ""
            hostKeyDialog.port = info.port || 0
            hostKeyDialog.keyType = info.keyType || ""
            hostKeyDialog.fingerprintSha256 = info.fingerprintSha256 || ""
            hostKeyDialog.fingerprintMd5 = info.fingerprintMd5 || ""
            hostKeyDialog.responded = false
            hostKeyDialog.open()
        }
        function onEditedFileUploadRequested(info) {
            root.pendingEditedFile = info || {}
            editedFileUploadDialog.open()
        }
    }

    Rectangle {
        anchors.fill: parent
        color: pageBg

        RowLayout {
            anchors.fill: parent
            spacing: 0

            // ============ Sidebar ============
            Rectangle {
                Layout.preferredWidth: 220
                Layout.fillHeight: true
                color: sidebarBg

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Label {
                            Layout.fillWidth: true
                            text: "连接管理"
                            color: textMain
                            font.pixelSize: 13
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }

                        IconButton {
                            iconName: "mdi6.plus"
                            tooltip: "新建连接"
                            accent: true
                            onClicked: openProfileEditor(null)
                        }
                    }

                    UiTextField {
                        id: sidebarFilter
                        Layout.fillWidth: true
                        dark: root.dark
                        placeholderText: "搜索连接"
                    }

                    ListView {
                        id: profileList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 4
                        model: remoteFilesVm.profiles
                        delegate: Rectangle {
                            id: profileRow

                            required property var modelData
                            required property int index
                            readonly property bool selected: root.selectedProfile && root.selectedProfile.id === modelData.id
                            readonly property string filterText: (sidebarFilter.text || "").toLowerCase()
                            readonly property bool matchesFilter: filterText.length === 0
                                || String(modelData.name || "").toLowerCase().indexOf(filterText) >= 0
                                || String(modelData.host || "").toLowerCase().indexOf(filterText) >= 0
                                || String(modelData.username || "").toLowerCase().indexOf(filterText) >= 0

                            width: ListView.view.width
                            height: matchesFilter ? 50 : 0
                            visible: matchesFilter
                            radius: 7
                            color: selected ? selectedBg : (profileMouse.containsMouse ? rowHover : "transparent")

                            MouseArea {
                                id: profileMouse

                                anchors.fill: parent
                                hoverEnabled: true
                                acceptedButtons: Qt.LeftButton | Qt.RightButton
                                cursorShape: Qt.PointingHandCursor
                                onClicked: function(mouse) {
                                    root.selectedProfile = modelData
                                    if (mouse.button === Qt.RightButton) {
                                        root.contextProfile = modelData
                                        root.openPopupAtMouse(profileMenu, profileMouse, mouse)
                                        return
                                    }
                                    if (root.sessionExists(modelData.id))
                                        remoteFilesVm.setActiveProfile(modelData.id || "")
                                }
                                onDoubleClicked: {
                                    if (root.sessionExists(modelData.id || "")) {
                                        remoteFilesVm.setActiveProfile(modelData.id || "")
                                    } else {
                                        remoteFilesVm.connectProfile(modelData.id || "")
                                    }
                                }
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 8
                                spacing: 8

                                Rectangle {
                                    Layout.preferredWidth: 6
                                    Layout.preferredHeight: 6
                                    radius: 3
                                    color: root.statusColorForId(modelData.id || "")
                                    visible: root.sessionExists(modelData.id || "")
                                }

                                Rectangle {
                                    Layout.preferredWidth: 28
                                    Layout.preferredHeight: 28
                                    radius: 7
                                    color: profileRow.selected
                                        ? Qt.rgba(1, 1, 1, 0.22)
                                        : (root.dark ? "#323A4A" : "#FFFFFF")
                                    border.width: profileRow.selected ? 0 : 1
                                    border.color: root.dark ? "#3F4759" : "#D5D8E0"

                                    UiIcon {
                                        anchors.centerIn: parent
                                        width: 16
                                        height: 16
                                        iconSize: 16
                                        name: "mdi6.server-network"
                                        color: profileRow.selected ? "#FFFFFF" : selectedBg
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 1

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 6

                                        Label {
                                            Layout.fillWidth: true
                                            text: modelData.name || "未命名连接"
                                            color: profileRow.selected ? "#FFFFFF" : textMain
                                            font.pixelSize: 12
                                            font.weight: Font.DemiBold
                                            elide: Text.ElideRight
                                        }

                                        Rectangle {
                                            Layout.preferredHeight: 15
                                            implicitWidth: protoLabel.implicitWidth + 10
                                            radius: 4
                                            color: profileRow.selected ? Qt.rgba(1, 1, 1, 0.26) : tagBg
                                            Label {
                                                id: protoLabel
                                                anchors.centerIn: parent
                                                text: (modelData.protocol || "").toUpperCase()
                                                color: profileRow.selected ? "#FFFFFF" : tagText
                                                font.pixelSize: 9
                                                font.weight: Font.DemiBold
                                            }
                                        }
                                    }

                                    Label {
                                        Layout.fillWidth: true
                                        text: root.profileSubtitle(modelData)
                                        color: profileRow.selected ? Qt.rgba(1, 1, 1, 0.92) : textMuted
                                        font.pixelSize: 10
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        text: (remoteFilesVm.profiles || []).length + " 个连接  ·  右键查看操作"
                        color: textFaint
                        font.pixelSize: 11
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }

            Rectangle {
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                color: separator
            }

            // ============ Right area ============
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                // Toolbar
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 44
                    color: toolbarBg

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 10

                        Rectangle {
                            width: 8
                            height: 8
                            radius: 4
                            color: root.statusColor()
                        }

                        Label {
                            text: root.selectedProfileName()
                            color: textMain
                            font.pixelSize: 13
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }

                        Label {
                            Layout.fillWidth: true
                            text: root.selectedProfileSubtitle() + "  ·  " + root.statusText()
                            color: errored ? danger : textMuted
                            font.pixelSize: 11
                            elide: Text.ElideRight
                        }

                        PushButton {
                            label: root.connecting ? "连接中" : (root.connected ? "已连接" : "连接")
                            accent: !root.connected
                            enabled: root.selectedProfile !== null && !root.connected && !root.connecting
                            iconName: "mdi6.connection"
                            onClicked: remoteFilesVm.connectProfile(root.selectedProfile ? root.selectedProfile.id || "" : "")
                        }

                        IconButton {
                            iconName: "mdi6.refresh"
                            tooltip: "刷新"
                            enabled: root.connected
                            onClicked: remoteFilesVm.refreshAll()
                        }

                        IconButton {
                            iconName: "mdi6.power"
                            tooltip: "断开"
                            dangerRole: true
                            enabled: root.connected || root.connecting
                            onClicked: remoteFilesVm.disconnect()
                        }
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        height: 1
                        color: separator
                    }
                }

                // Main split: remote | terminal
                SplitView {
                    id: mainSplit
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    orientation: Qt.Horizontal
                    handle: Rectangle {
                        implicitWidth: 1
                        implicitHeight: 1
                        color: separator
                    }

                    RemoteFilePane {
                        id: remotePane
                        SplitView.preferredWidth: 520
                        SplitView.minimumWidth: 320
                        enabled: root.connected
                    }

                    StackLayout {
                        id: rightStack
                        SplitView.fillWidth: true
                        SplitView.minimumWidth: 280
                        currentIndex: {
                            if (root.rightPaneMode === "empty") return 0
                            if (root.rightPaneMode === "ftp") return 1
                            var activeId = remoteFilesVm.activeProfileId || ""
                            for (var i = 0; i < root.sftpSessionList.length; i++) {
                                if (root.sftpSessionList[i].profileId === activeId)
                                    return 2 + i
                            }
                            return 0
                        }

                        Rectangle {
                            color: dark ? "#101014" : "#FFFFFF"
                            Label {
                                anchors.centerIn: parent
                                text: "未选中连接"
                                color: textFaint
                                font.pixelSize: 13
                            }
                        }

                        FtpLogPane { id: ftpLogPane }

                        Repeater {
                            id: terminalRepeater
                            model: root.sftpSessionList
                            TerminalPane {
                                required property var modelData
                                bridge: remoteFilesVm.terminalBridgeForProfile(modelData.profileId || "")
                            }
                        }
                    }
                }

                // Transfers panel
                Rectangle {
                    id: transfersBar
                    property bool collapsed: false

                    Layout.fillWidth: true
                    Layout.preferredHeight: collapsed ? 36 : 210
                    color: surface

                    Behavior on Layout.preferredHeight { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        height: 1
                        color: separator
                    }

                    Rectangle {
                        id: transfersHeader
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.topMargin: 1
                        height: 35
                        color: toolbarBg

                        MouseArea {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            width: 240
                            cursorShape: Qt.PointingHandCursor
                            onClicked: transfersBar.collapsed = !transfersBar.collapsed
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 10
                            spacing: 10

                            UiIcon {
                                Layout.preferredWidth: 14
                                Layout.preferredHeight: 14
                                iconSize: 14
                                name: transfersBar.collapsed ? "mdi6.chevron-right" : "mdi6.chevron-down"
                                color: textMuted
                            }

                            Label {
                                text: "传输队列"
                                color: textMain
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                            }

                            Label {
                                text: (remoteFilesVm.transfers || []).length > 0
                                    ? "(" + (remoteFilesVm.transfers || []).length + ")"
                                    : ""
                                color: textFaint
                                font.pixelSize: 12
                            }

                            Item { Layout.fillWidth: true }

                            IconButton {
                                iconName: "mdi6.broom"
                                tooltip: "清理已完成"
                                onClicked: remoteFilesVm.clearFinishedTransfers()
                            }
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            height: 1
                            color: separator
                            visible: !transfersBar.collapsed
                        }
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: transfersHeader.bottom
                        height: 22
                        color: surface
                        visible: !transfersBar.collapsed && (remoteFilesVm.transfers || []).length > 0

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 14
                            spacing: 10
                            Label { Layout.preferredWidth: 18; text: "" }
                            Label { Layout.preferredWidth: 130; text: "文件"; color: textFaint; font.pixelSize: 10 }
                            Label { Layout.fillWidth: true; text: "本地路径"; color: textFaint; font.pixelSize: 10 }
                            Label { Layout.fillWidth: true; text: "远程路径"; color: textFaint; font.pixelSize: 10 }
                            Label { Layout.preferredWidth: 160; text: "进度"; color: textFaint; font.pixelSize: 10 }
                            Label { Layout.preferredWidth: 60; text: "状态"; color: textFaint; font.pixelSize: 10 }
                            Label { Layout.preferredWidth: 28; text: "" }
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            height: 1
                            color: separator
                        }
                    }

                    ListView {
                        id: transferList
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: transfersHeader.bottom
                        anchors.topMargin: (remoteFilesVm.transfers || []).length > 0 ? 22 : 0
                        anchors.bottom: parent.bottom
                        clip: true
                        visible: !transfersBar.collapsed
                        model: remoteFilesVm.transfers
                        delegate: Rectangle {
                            required property var modelData
                            required property int index

                            width: ListView.view.width
                            height: 32
                            color: index % 2 === 0 ? surface : surfaceSubtle

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 14
                                anchors.rightMargin: 14
                                spacing: 10

                                UiIcon {
                                    Layout.preferredWidth: 14
                                    Layout.preferredHeight: 14
                                    iconSize: 14
                                    name: modelData.direction === "upload" ? "mdi6.arrow-up-bold" : "mdi6.arrow-down-bold"
                                    color: modelData.direction === "upload" ? success : selectedBg
                                }

                                Label {
                                    Layout.preferredWidth: 130
                                    text: modelData.name || ""
                                    color: textMain
                                    font.pixelSize: 12
                                    elide: Text.ElideMiddle
                                }

                                Label {
                                    Layout.fillWidth: true
                                    text: root.shortenPath(modelData.localPath || "", 60)
                                    color: textMuted
                                    font.pixelSize: 11
                                    elide: Text.ElideLeft
                                    ToolTip.visible: localPathHover.containsMouse && (modelData.localPath || "").length > 0
                                    ToolTip.text: modelData.localPath || ""
                                    ToolTip.delay: 600
                                    MouseArea {
                                        id: localPathHover
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        acceptedButtons: Qt.NoButton
                                    }
                                }

                                Label {
                                    Layout.fillWidth: true
                                    text: root.shortenPath(modelData.remotePath || "", 60)
                                    color: textMuted
                                    font.pixelSize: 11
                                    elide: Text.ElideLeft
                                    ToolTip.visible: remotePathHover.containsMouse && (modelData.remotePath || "").length > 0
                                    ToolTip.text: modelData.remotePath || ""
                                    ToolTip.delay: 600
                                    MouseArea {
                                        id: remotePathHover
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        acceptedButtons: Qt.NoButton
                                    }
                                }

                                ProgressBar {
                                    Layout.preferredWidth: 160
                                    Layout.preferredHeight: 6
                                    from: 0
                                    to: 100
                                    value: modelData.progress || 0
                                }

                                Label {
                                    text: {
                                        var status = modelData.status || ""
                                        if (status === "queued") return "等待"
                                        if (status === "running") return (modelData.progress || 0) + "%"
                                        if (status === "completed") return "完成"
                                        if (status === "cancelled") return "已取消"
                                        if (status === "failed") return "失败"
                                        return status
                                    }
                                    color: {
                                        var status = modelData.status || ""
                                        if (status === "failed") return danger
                                        if (status === "completed") return success
                                        return textMuted
                                    }
                                    font.pixelSize: 11
                                    Layout.preferredWidth: 60
                                }

                                IconButton {
                                    iconName: "mdi6.close"
                                    tooltip: "取消"
                                    enabled: modelData.status === "queued" || modelData.status === "running"
                                    onClicked: remoteFilesVm.cancelTransfer(modelData.id || "")
                                }
                            }
                        }

                        Label {
                            anchors.centerIn: parent
                            visible: (remoteFilesVm.transfers || []).length === 0
                            text: "暂无传输任务  ·  右键远程文件下载，或拖拽文件夹到目录上传"
                            color: textFaint
                            font.pixelSize: 12
                        }
                    }
                }
            }
        }
    }

    // ============ Menus ============
    function openPopupAtMouse(popup, srcItem, mouse) {
        if (popup.openAt) {
            popup.openAt(srcItem, mouse.x, mouse.y)
            return
        }
        var p = srcItem.mapToItem(Overlay.overlay, mouse.x, mouse.y)
        popup.x = p.x
        popup.y = p.y
        popup.open()
    }

    UiMenuPopup {
        id: profileMenu
        width: 200
        dark: root.dark

        contentItem: Column {
            id: profileMenuColumn
            spacing: 0

            UiMenuItem {
                width: profileMenu.width - 8
                dark: root.dark
                text: "连接"
                onTriggered: {
                    if (root.contextProfile) remoteFilesVm.connectProfile(root.contextProfile.id || "")
                    profileMenu.close()
                }
            }
            UiMenuItem {
                width: profileMenu.width - 8
                dark: root.dark
                text: "切换至此会话"
                itemEnabled: root.contextProfile && root.sessionExists(root.contextProfile.id || "")
                onTriggered: {
                    if (root.contextProfile) remoteFilesVm.setActiveProfile(root.contextProfile.id || "")
                    profileMenu.close()
                }
            }
            UiMenuItem {
                width: profileMenu.width - 8
                dark: root.dark
                text: "断开此连接"
                destructive: true
                itemEnabled: root.contextProfile && root.sessionExists(root.contextProfile.id || "")
                onTriggered: {
                    if (root.contextProfile) remoteFilesVm.disconnectProfile(root.contextProfile.id || "")
                    profileMenu.close()
                }
            }
            UiMenuSeparator { width: profileMenu.width - 8; dark: root.dark }
            UiMenuItem {
                width: profileMenu.width - 8
                dark: root.dark
                text: "编辑…"
                onTriggered: { openProfileEditor(root.contextProfile); profileMenu.close() }
            }
            UiMenuItem {
                width: profileMenu.width - 8
                dark: root.dark
                text: "复制连接"
                onTriggered: { duplicateProfile(root.contextProfile); profileMenu.close() }
            }
            UiMenuSeparator { width: profileMenu.width - 8; dark: root.dark }
            UiMenuItem {
                width: profileMenu.width - 8
                dark: root.dark
                destructive: true
                text: "删除"
                onTriggered: {
                    if (root.contextProfile) remoteFilesVm.deleteProfile(root.contextProfile.id || "")
                    profileMenu.close()
                }
            }
        }
    }

    UiMenuPopup {
        id: remoteFileMenu
        width: 220
        dark: root.dark
        property bool itemIsDir: root.contextItem ? !!root.contextItem.isDir : false
        property bool hasItem: root.contextItem !== null
        property bool itemIsParent: root.contextItem && root.contextItem.name === ".."
        property bool itemCanEditFile: remoteFileMenu.hasItem && !remoteFileMenu.itemIsDir && remoteFilesVm.canEditRemoteFile(root.contextItem)

        contentItem: Column {
            id: remoteFileMenuColumn
            spacing: 0

            UiMenuItem {
                width: remoteFileMenu.width - 8
                dark: root.dark
                itemEnabled: remoteFileMenu.hasItem
                text: remoteFileMenu.itemIsDir ? "打开目录" : "下载到默认目录"
                onTriggered: {
                    if (!root.contextItem) return
                    if (root.contextItem.isDir)
                        remoteFilesVm.changeRemotePath(root.contextItem.path || "")
                    else
                        remoteFilesVm.downloadFiles([root.contextItem])
                    remoteFileMenu.close()
                }
            }
            UiMenuItem {
                width: remoteFileMenu.width - 8
                dark: root.dark
                itemEnabled: remoteFileMenu.hasItem && !remoteFileMenu.itemIsDir
                text: "下载到…"
                onTriggered: { downloadFolderDialog.open(); remoteFileMenu.close() }
            }
            UiMenuItem {
                width: remoteFileMenu.width - 8
                dark: root.dark
                itemEnabled: remoteFileMenu.itemCanEditFile
                text: "编辑…"
                onTriggered: {
                    if (!root.contextItem) return
                    remoteFilesVm.editRemoteFile(root.contextItem)
                    remoteFileMenu.close()
                }
            }
            UiMenuSeparator { width: remoteFileMenu.width - 8; dark: root.dark }
            UiMenuItem {
                width: remoteFileMenu.width - 8
                dark: root.dark
                itemEnabled: root.connected
                text: "新建目录…"
                onTriggered: { mkdirDialog.open(); remoteFileMenu.close() }
            }
            UiMenuItem {
                width: remoteFileMenu.width - 8
                dark: root.dark
                itemEnabled: remoteFileMenu.hasItem && !remoteFileMenu.itemIsParent
                text: "重命名…"
                onTriggered: {
                    if (!root.contextItem) return
                    renameDialog.targetPath = root.contextItem.path || ""
                    renameField.text = root.contextItem.name || ""
                    renameDialog.open()
                    remoteFileMenu.close()
                }
            }
            UiMenuItem {
                width: remoteFileMenu.width - 8
                dark: root.dark
                itemEnabled: root.connected
                text: "刷新"
                onTriggered: { remoteFilesVm.changeRemotePath(remoteFilesVm.remotePath); remoteFileMenu.close() }
            }
            UiMenuSeparator { width: remoteFileMenu.width - 8; dark: root.dark }
            UiMenuItem {
                width: remoteFileMenu.width - 8
                dark: root.dark
                destructive: true
                itemEnabled: remoteFileMenu.hasItem && !remoteFileMenu.itemIsParent
                text: "删除"
                onTriggered: {
                    if (!root.contextItem) return
                    root.selectedRemoteItems = [root.contextItem]
                    deleteDialog.open()
                    remoteFileMenu.close()
                }
            }
        }
    }

    // ============ Dialogs ============
    Dialog {
        id: profileDialog
        modal: true
        title: ""
        width: 620
        height: 600
        anchors.centerIn: Overlay.overlay
        padding: 0

        property bool showAdvanced: false

        background: Rectangle {
            color: surface
            radius: 14
            border.width: 1
            border.color: dark ? "#3D4555" : "#D8DAE2"
        }

        header: Rectangle {
            color: "transparent"
            implicitHeight: 72
            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: 28
                anchors.rightMargin: 28
                anchors.topMargin: 18
                anchors.bottomMargin: 14
                spacing: 4

                Label {
                    text: editingProfile.id ? "编辑连接" : "新建连接"
                    color: textMain
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                }
                Label {
                    text: "为 SFTP / FTP / FTPS 服务器配置访问凭据。"
                    color: textMuted
                    font.pixelSize: 12
                }
            }
        }

        footer: Rectangle {
            color: surfaceSubtle
            implicitHeight: 58
            radius: 14

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 1
                color: separator
            }

            // mask bottom rounded corners against bg
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 14
                color: surfaceSubtle
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 24
                spacing: 12

                Label {
                    Layout.fillWidth: true
                    text: "敏感信息以明文方式保存到本地数据库。"
                    color: textFaint
                    font.pixelSize: 11
                    elide: Text.ElideRight
                }

                PushButton {
                    label: "取消"
                    onClicked: profileDialog.close()
                }

                PushButton {
                    label: "保存"
                    accent: true
                    onClicked: profileDialog.accept()
                }
            }
        }

        onOpened: root.resetProfileDialogFields()

        onAccepted: {
            var p = copyProfile(editingProfile)
            p.name = nameField.text
            p.protocol = ["sftp", "ftp", "ftps"][protocolBox.currentIndex]
            p.host = hostField.text
            p.port = parseInt(portField.text || "0")
            p.username = usernameField.text
            p.password = passwordField.text
            p.remoteRoot = remoteRootField.text
            p.localRoot = localRootField.text
            p.encoding = encodingField.text || "utf-8"
            p.passiveMode = passiveSwitch.checked
            p.authKind = ["password", "private_key", "agent"][authBox.currentIndex]
            p.privateKeyPath = keyPathField.text
            p.privateKeyPassphrase = keyPassField.text
            p.connectTimeout = parseInt(timeoutField.text || "15")
            p.jumpEnabled = jumpSwitch.checked
            p.jumpHost = jumpHostField.text
            p.jumpPort = parseInt(jumpPortField.text || "22")
            p.jumpUsername = jumpUserField.text
            p.jumpPassword = jumpPasswordField.text
            p.jumpPrivateKeyPath = jumpKeyField.text
            p.jumpPrivateKeyPassphrase = jumpKeyPassField.text
            remoteFilesVm.saveProfile(p)
        }

        contentItem: ScrollView {
            id: dialogScroll
            clip: true
            contentWidth: availableWidth
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                width: dialogScroll.availableWidth
                spacing: 18

                // Section: 通用
                MacCard {
                    Layout.leftMargin: 24
                    Layout.rightMargin: 24
                    Layout.fillWidth: true
                    title: "通用"

                    MacFormItem {
                        label: "名称"
                        UiTextField {
                            id: nameField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.name || ""
                            placeholderText: "例如：生产环境跳板"
                        }
                    }
                    MacFormDivider {}
                    MacFormItem {
                        label: "协议"
                        UiComboBox {
                            id: protocolBox
                            dark: root.dark
                            Layout.preferredWidth: 200
                            model: ["SFTP", "FTP", "FTPS"]
                            currentIndex: (editingProfile.protocol || "sftp") === "ftp"
                                ? 1
                                : (editingProfile.protocol || "sftp") === "ftps" ? 2 : 0
                            onCurrentIndexChanged: {
                                if (portField.text === "" || portField.text === "22" || portField.text === "21")
                                    portField.text = currentIndex === 0 ? "22" : "21"
                            }
                        }
                    }
                }

                // Section: 服务器
                MacCard {
                    Layout.leftMargin: 24
                    Layout.rightMargin: 24
                    Layout.fillWidth: true
                    title: "服务器"

                    MacFormItem {
                        label: "主机"
                        UiTextField {
                            id: hostField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.host || ""
                            placeholderText: "host 或 IP"
                        }
                    }
                    MacFormDivider {}
                    MacFormItem {
                        label: "端口"
                        UiTextField {
                            id: portField
                            dark: root.dark
                            Layout.preferredWidth: 120
                            text: String(editingProfile.port || ((editingProfile.protocol || "sftp") === "sftp" ? 22 : 21))
                        }
                    }
                    MacFormDivider {}
                    MacFormItem {
                        label: "用户名"
                        UiTextField {
                            id: usernameField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.username || ""
                            placeholderText: "登录账号"
                        }
                    }
                }

                // Section: 认证
                MacCard {
                    Layout.leftMargin: 24
                    Layout.rightMargin: 24
                    Layout.fillWidth: true
                    title: "身份认证"

                    MacFormItem {
                        label: "方式"
                        UiComboBox {
                            id: authBox
                            dark: root.dark
                            Layout.preferredWidth: 200
                            model: ["密码", "私钥", "SSH Agent"]
                            currentIndex: (editingProfile.authKind || "password") === "private_key"
                                ? 1
                                : (editingProfile.authKind || "password") === "agent" ? 2 : 0
                        }
                    }

                    MacFormDivider { visible: authBox.currentIndex === 0 }
                    MacFormItem {
                        visible: authBox.currentIndex === 0
                        label: "密码"
                        UiTextField {
                            id: passwordField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.password || ""
                            echoMode: TextInput.Password
                            placeholderText: "登录密码"
                        }
                    }

                    MacFormDivider { visible: authBox.currentIndex === 1 }
                    MacFormItem {
                        visible: authBox.currentIndex === 1
                        label: "私钥"
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            UiTextField {
                                id: keyPathField
                                dark: root.dark
                                Layout.fillWidth: true
                                text: editingProfile.privateKeyPath || ""
                                placeholderText: "~/.ssh/id_rsa"
                            }
                            PushButton {
                                label: "选择…"
                                onClicked: keyFileDialog.open()
                            }
                        }
                    }

                    MacFormDivider { visible: authBox.currentIndex === 1 }
                    MacFormItem {
                        visible: authBox.currentIndex === 1
                        label: "口令"
                        UiTextField {
                            id: keyPassField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.privateKeyPassphrase || ""
                            echoMode: TextInput.Password
                            placeholderText: "可选"
                        }
                    }
                }

                // Advanced toggle
                Rectangle {
                    Layout.leftMargin: 24
                    Layout.rightMargin: 24
                    Layout.fillWidth: true
                    Layout.preferredHeight: 38
                    radius: 9
                    color: surfaceSubtle
                    border.width: 1
                    border.color: separator

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 8

                        UiIcon {
                            Layout.preferredWidth: 14
                            Layout.preferredHeight: 14
                            iconSize: 14
                            name: profileDialog.showAdvanced ? "mdi6.chevron-down" : "mdi6.chevron-right"
                            color: textMuted
                        }

                        Label {
                            Layout.fillWidth: true
                            text: "高级选项"
                            color: textMain
                            font.pixelSize: 12
                            font.weight: Font.Medium
                        }

                        Label {
                            text: "默认目录 · 编码 · 超时 · 跳板机"
                            color: textFaint
                            font.pixelSize: 11
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: profileDialog.showAdvanced = !profileDialog.showAdvanced
                    }
                }

                // Section: advanced
                MacCard {
                    visible: profileDialog.showAdvanced
                    Layout.leftMargin: 24
                    Layout.rightMargin: 24
                    Layout.fillWidth: true
                    title: "高级"

                    MacFormItem {
                        label: "远程默认目录"
                        UiTextField {
                            id: remoteRootField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.remoteRoot || ""
                            placeholderText: "留空则使用远程家目录"
                        }
                    }
                    MacFormDivider {}
                    MacFormItem {
                        label: "本地默认目录"
                        UiTextField {
                            id: localRootField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.localRoot || ""
                            placeholderText: "留空则使用本机家目录"
                        }
                    }
                    MacFormDivider {}
                    MacFormItem {
                        label: "编码"
                        UiTextField {
                            id: encodingField
                            dark: root.dark
                            Layout.preferredWidth: 160
                            text: editingProfile.encoding || "utf-8"
                        }
                    }
                    MacFormDivider {}
                    MacFormItem {
                        label: "连接超时 (秒)"
                        UiTextField {
                            id: timeoutField
                            dark: root.dark
                            Layout.preferredWidth: 120
                            text: String(editingProfile.connectTimeout || 15)
                        }
                    }
                    MacFormDivider {}
                    MacFormItem {
                        label: "FTP 被动模式"
                        UiSwitch {
                            id: passiveSwitch
                            dark: root.dark
                            checked: editingProfile.passiveMode !== false
                        }
                    }
                }

                MacCard {
                    visible: profileDialog.showAdvanced
                    Layout.leftMargin: 24
                    Layout.rightMargin: 24
                    Layout.fillWidth: true
                    title: "跳板机"

                    MacFormItem {
                        label: "启用"
                        UiSwitch {
                            id: jumpSwitch
                            dark: root.dark
                            checked: editingProfile.jumpEnabled || false
                        }
                    }
                    MacFormDivider { visible: jumpSwitch.checked }
                    MacFormItem {
                        visible: jumpSwitch.checked
                        label: "主机"
                        UiTextField {
                            id: jumpHostField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.jumpHost || ""
                        }
                    }
                    MacFormDivider { visible: jumpSwitch.checked }
                    MacFormItem {
                        visible: jumpSwitch.checked
                        label: "端口"
                        UiTextField {
                            id: jumpPortField
                            dark: root.dark
                            Layout.preferredWidth: 120
                            text: String(editingProfile.jumpPort || 22)
                        }
                    }
                    MacFormDivider { visible: jumpSwitch.checked }
                    MacFormItem {
                        visible: jumpSwitch.checked
                        label: "用户名"
                        UiTextField {
                            id: jumpUserField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.jumpUsername || ""
                        }
                    }
                    MacFormDivider { visible: jumpSwitch.checked }
                    MacFormItem {
                        visible: jumpSwitch.checked
                        label: "密码"
                        UiTextField {
                            id: jumpPasswordField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.jumpPassword || ""
                            echoMode: TextInput.Password
                        }
                    }
                    MacFormDivider { visible: jumpSwitch.checked }
                    MacFormItem {
                        visible: jumpSwitch.checked
                        label: "私钥"
                        UiTextField {
                            id: jumpKeyField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.jumpPrivateKeyPath || ""
                        }
                    }
                    MacFormDivider { visible: jumpSwitch.checked }
                    MacFormItem {
                        visible: jumpSwitch.checked
                        label: "私钥口令"
                        UiTextField {
                            id: jumpKeyPassField
                            dark: root.dark
                            Layout.fillWidth: true
                            text: editingProfile.jumpPrivateKeyPassphrase || ""
                            echoMode: TextInput.Password
                        }
                    }
                }

                Item { Layout.preferredHeight: 8 }
            }
        }
    }

    FileDialog {
        id: keyFileDialog
        title: "选择私钥文件"
        onAccepted: {
            var url = selectedFile.toString()
            if (url.indexOf("file://") === 0)
                url = decodeURIComponent(url.substring(7))
            keyPathField.text = url
        }
    }

    FileDialog {
        id: uploadFileDialog
        title: "选择要上传的文件"
        fileMode: FileDialog.OpenFiles
        onAccepted: {
            var paths = []
            var files = selectedFiles
            for (var i = 0; i < files.length; i++)
                paths.push(files[i].toString())
            if (paths.length > 0)
                remoteFilesVm.uploadPaths(paths)
        }
    }

    FolderDialog {
        id: downloadFolderDialog
        title: "选择下载到的目录"
        onAccepted: {
            if (!root.contextItem)
                return
            var url = selectedFolder.toString()
            remoteFilesVm.downloadFilesTo([root.contextItem], url)
        }
    }

    Dialog {
        id: mkdirDialog
        modal: true
        title: "新建远程目录"
        standardButtons: Dialog.Ok | Dialog.Cancel
        anchors.centerIn: Overlay.overlay
        onAccepted: {
            remoteFilesVm.mkdirRemote(mkdirField.text)
            mkdirField.text = ""
        }
        UiTextField { id: mkdirField; dark: root.dark; width: 320; placeholderText: "目录名" }
    }

    Dialog {
        id: renameDialog
        property string targetPath: ""
        modal: true
        title: "重命名"
        standardButtons: Dialog.Ok | Dialog.Cancel
        anchors.centerIn: Overlay.overlay
        onAccepted: remoteFilesVm.renameRemote(targetPath, renameField.text)
        UiTextField { id: renameField; dark: root.dark; width: 320; placeholderText: "新名称" }
    }

    Dialog {
        id: deleteDialog
        modal: true
        anchors.centerIn: Overlay.overlay
        width: 390
        padding: 0
        closePolicy: Popup.CloseOnEscape

        background: UiPopupSurface {
            dark: root.dark
            radius: 14
            fillColor: surface
        }

        contentItem: ColumnLayout {
            spacing: 18

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 22
                Layout.rightMargin: 22
                Layout.topMargin: 22
                spacing: 14

                Rectangle {
                    Layout.preferredWidth: 38
                    Layout.preferredHeight: 38
                    Layout.alignment: Qt.AlignTop
                    radius: 10
                    color: dark ? Qt.rgba(1, 0.27, 0.23, 0.16) : Qt.rgba(1, 0.23, 0.18, 0.10)

                    UiIcon {
                        anchors.centerIn: parent
                        width: 21
                        height: 21
                        iconSize: 21
                        name: "mdi6.trash-can-outline"
                        color: danger
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    Label {
                        Layout.fillWidth: true
                        text: "删除远程项目？"
                        color: textMain
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    Label {
                        Layout.fillWidth: true
                        text: "选中的文件或目录会从服务器删除。目录会连同内部内容一起删除。"
                        color: textMuted
                        font.pixelSize: 12
                        lineHeight: 1.15
                        wrapMode: Text.WordWrap
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 22
                Layout.rightMargin: 22
                Layout.bottomMargin: 20
                spacing: 8

                Item { Layout.fillWidth: true }

                PushButton {
                    label: "取消"
                    onClicked: deleteDialog.close()
                }

                PushButton {
                    label: "删除"
                    dangerRole: true
                    onClicked: {
                        remoteFilesVm.deleteRemote(root.selectedRemoteItems)
                        deleteDialog.close()
                    }
                }
            }
        }
    }

    Dialog {
        id: editedFileUploadDialog
        modal: true
        anchors.centerIn: Overlay.overlay
        width: 440
        padding: 0
        closePolicy: Popup.CloseOnEscape

        background: UiPopupSurface {
            dark: root.dark
            radius: 14
            fillColor: surface
        }

        contentItem: ColumnLayout {
            spacing: 18

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 22
                Layout.rightMargin: 22
                Layout.topMargin: 22
                spacing: 14

                Rectangle {
                    Layout.preferredWidth: 38
                    Layout.preferredHeight: 38
                    Layout.alignment: Qt.AlignTop
                    radius: 10
                    color: dark ? Qt.rgba(0.10, 0.52, 1.0, 0.18) : Qt.rgba(0.10, 0.52, 1.0, 0.10)

                    UiIcon {
                        anchors.centerIn: parent
                        width: 21
                        height: 21
                        iconSize: 21
                        name: "mdi6.cloud-upload-outline"
                        color: selectedBg
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Label {
                        Layout.fillWidth: true
                        text: "回传编辑后的文件？"
                        color: textMain
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    Label {
                        Layout.fillWidth: true
                        text: "检测到本地编辑副本已保存，是否上传覆盖服务器上的同名文件？"
                        color: textMuted
                        font.pixelSize: 12
                        lineHeight: 1.15
                        wrapMode: Text.WordWrap
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 72
                        radius: 8
                        color: dark ? "#232837" : "#F4F6FA"
                        border.width: 1
                        border.color: dark ? "#3A4252" : "#E1E4EC"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 5

                            Label {
                                Layout.fillWidth: true
                                text: root.pendingEditedFile.remotePath || ""
                                color: textMain
                                font.pixelSize: 12
                                elide: Text.ElideMiddle
                            }

                            Label {
                                Layout.fillWidth: true
                                text: root.pendingEditedFile.localPath || ""
                                color: textMuted
                                font.pixelSize: 11
                                elide: Text.ElideMiddle
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 22
                Layout.rightMargin: 22
                Layout.bottomMargin: 20
                spacing: 8

                Item { Layout.fillWidth: true }

                PushButton {
                    label: "暂不回传"
                    onClicked: {
                        remoteFilesVm.skipEditedFileUpload(root.pendingEditedFile.id || "")
                        editedFileUploadDialog.close()
                    }
                }

                PushButton {
                    label: "回传"
                    accent: true
                    onClicked: {
                        remoteFilesVm.uploadEditedFile(root.pendingEditedFile.id || "")
                        editedFileUploadDialog.close()
                    }
                }
            }
        }

        onClosed: root.pendingEditedFile = ({})
    }

    Dialog {
        id: hostKeyDialog
        modal: true
        closePolicy: Popup.NoAutoClose
        anchors.centerIn: Overlay.overlay
        width: 520
        padding: 0

        property string profileId: ""
        property string host: ""
        property int port: 0
        property string keyType: ""
        property string fingerprintSha256: ""
        property string fingerprintMd5: ""
        property bool responded: false

        background: Rectangle {
            color: surface
            radius: 14
            border.width: 1
            border.color: dark ? "#3D4555" : "#D8DAE2"
        }

        header: Rectangle {
            color: "transparent"
            implicitHeight: 72
            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 24
                anchors.topMargin: 18
                anchors.bottomMargin: 12
                spacing: 4
                Label {
                    text: "确认主机指纹"
                    color: textMain
                    font.pixelSize: 17
                    font.weight: Font.DemiBold
                }
                Label {
                    text: "首次连接到该主机。请核对指纹后再继续。"
                    color: textMuted
                    font.pixelSize: 12
                }
            }
        }

        footer: Rectangle {
            color: surfaceSubtle
            implicitHeight: 58
            radius: 14

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 1
                color: separator
            }
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 14
                color: surfaceSubtle
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 24
                spacing: 12

                Label {
                    Layout.fillWidth: true
                    text: "接受将写入 ~/.ssh/known_hosts。"
                    color: textFaint
                    font.pixelSize: 11
                    elide: Text.ElideRight
                }

                PushButton {
                    label: "拒绝"
                    onClicked: hostKeyDialog.reject()
                }
                PushButton {
                    label: "接受"
                    accent: true
                    onClicked: hostKeyDialog.accept()
                }
            }
        }

        contentItem: ColumnLayout {
            spacing: 10

            Item { Layout.preferredHeight: 4 }

            GridLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 24
                Layout.rightMargin: 24
                columns: 2
                columnSpacing: 16
                rowSpacing: 8

                Label { text: "主机"; color: textMuted; font.pixelSize: 12 }
                Label {
                    text: hostKeyDialog.host + (hostKeyDialog.port > 0 ? (":" + hostKeyDialog.port) : "")
                    color: textMain
                    font.pixelSize: 13
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }

                Label { text: "密钥类型"; color: textMuted; font.pixelSize: 12 }
                Label {
                    text: hostKeyDialog.keyType
                    color: textMain
                    font.pixelSize: 13
                    Layout.fillWidth: true
                }

                Label { text: "SHA256"; color: textMuted; font.pixelSize: 12 }
                Label {
                    text: hostKeyDialog.fingerprintSha256
                    color: textMain
                    font.pixelSize: 12
                    font.family: Theme.fontFamily.mono
                    Layout.fillWidth: true
                    wrapMode: Text.WrapAnywhere
                }

                Label { text: "MD5"; color: textMuted; font.pixelSize: 12 }
                Label {
                    text: hostKeyDialog.fingerprintMd5
                    color: textMain
                    font.pixelSize: 12
                    font.family: Theme.fontFamily.mono
                    Layout.fillWidth: true
                    wrapMode: Text.WrapAnywhere
                }
            }

            Item { Layout.preferredHeight: 8 }
        }

        onAccepted: {
            hostKeyDialog.responded = true
            remoteFilesVm.respondHostKeyPrompt(hostKeyDialog.profileId, true)
        }
        onRejected: {
            hostKeyDialog.responded = true
            remoteFilesVm.respondHostKeyPrompt(hostKeyDialog.profileId, false)
        }
        onClosed: {
            if (!hostKeyDialog.responded && hostKeyDialog.profileId.length > 0) {
                remoteFilesVm.respondHostKeyPrompt(hostKeyDialog.profileId, false)
            }
            hostKeyDialog.responded = true
        }
    }

    Rectangle {
        id: toast
        parent: Overlay.overlay
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.rightMargin: 18
        anchors.topMargin: 18
        width: Math.min(parent ? parent.width - 36 : 360, Math.max(280, toastLabel.implicitWidth + 84))
        height: 52
        radius: 8
        color: dark ? "#163A5C" : "#E8F3FF"
        border.width: 1
        border.color: selectedBg
        opacity: 0
        visible: opacity > 0
        z: 1000
        property string text: ""

        function show(message) {
            text = String(message || "")
            opacity = 0.96
            toastTimer.restart()
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 14
            anchors.rightMargin: 14
            spacing: 10

            Rectangle {
                Layout.preferredWidth: 28
                Layout.preferredHeight: 28
                radius: 14
                color: selectedBg

                UiIcon {
                    anchors.centerIn: parent
                    width: 16
                    height: 16
                    iconSize: 16
                    name: "mdi6.cloud-upload-outline"
                    color: "#FFFFFF"
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1

                Label {
                    text: "操作提示"
                    color: dark ? "#FFFFFF" : "#0D3154"
                    font.pixelSize: 11
                    font.weight: Font.DemiBold
                }

                Label {
                    id: toastLabel
                    Layout.fillWidth: true
                    text: toast.text
                    color: dark ? "#EAF4FF" : "#16456F"
                    font.pixelSize: 12
                    elide: Text.ElideRight
                }
            }
        }

        Behavior on opacity { NumberAnimation { duration: 160 } }
        Timer {
            id: toastTimer
            interval: 2400
            onTriggered: {
                toast.opacity = 0
                root.lastToastMessage = ""
            }
        }
    }

    // ============ Components ============

    component MacCard: ColumnLayout {
        property string title: ""
        default property alias content: cardCol.data
        Layout.fillWidth: true
        spacing: 6

        children: [
            Label {
                visible: title.length > 0
                text: title
                color: textFaint
                font.pixelSize: 11
                font.weight: Font.Medium
                font.capitalization: Font.AllUppercase
                Layout.leftMargin: 2
            },
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: cardCol.implicitHeight + 4
                radius: 10
                color: surfaceElevated
                border.width: 1
                border.color: dark ? "#3D4555" : "#E2E4EB"

                ColumnLayout {
                    id: cardCol
                    anchors.fill: parent
                    anchors.margins: 2
                    spacing: 0
                }
            }
        ]
    }

    component MacFormDivider: Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 1
        Layout.leftMargin: 14
        color: separator
    }

    component MacFormItem: RowLayout {
        property string label: ""
        spacing: 14
        Layout.fillWidth: true
        Layout.minimumHeight: 38

        Label {
            text: parent.label
            color: textMain
            font.pixelSize: 12
            Layout.preferredWidth: 110
            Layout.leftMargin: 14
            horizontalAlignment: Text.AlignRight
            verticalAlignment: Text.AlignVCenter
        }
    }

    component RemoteFilePane: Rectangle {
        id: pane

        color: surface
        border.width: 0

        function currentItem() {
            if (fileList.currentIndex < 0 || fileList.currentIndex >= (remoteFilesVm.remoteItems || []).length)
                return null
            return remoteFilesVm.remoteItems[fileList.currentIndex]
        }

        function acceptFileDrop(event) {
            if (!event || !event.hasUrls) {
                if (event)
                    event.accepted = false
                return false
            }
            event.accept(Qt.CopyAction)
            if (event.acceptProposedAction)
                event.acceptProposedAction()
            event.accepted = true
            return true
        }

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            // Title bar
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 42
                color: toolbarBg

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 12
                    spacing: 10

                    UiIcon {
                        Layout.preferredWidth: 14
                        Layout.preferredHeight: 14
                        iconSize: 14
                        name: "mdi6.folder-network-outline"
                        color: selectedBg
                    }

                    Label {
                        text: "远程目录"
                        color: textMain
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                    }

                    Item { Layout.fillWidth: true }

                    IconButton {
                        iconName: "mdi6.console-network-outline"
                        tooltip: "同步至终端目录"
                        enabled: pane.enabled && root.sftpConnected
                        onClicked: remoteFilesVm.syncRemoteFromTerminal()
                    }

                    Label {
                        text: (remoteFilesVm.remoteItems || []).length + " 项"
                        color: textFaint
                        font.pixelSize: 11
                    }
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: 1
                    color: separator
                }
            }

            // Path bar
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                color: surface

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 6

                    IconButton {
                        iconName: "mdi6.arrow-up"
                        tooltip: "返回上级"
                        enabled: pane.enabled && remoteFilesVm.remotePath !== "/"
                        onClicked: {
                            var p = String(remoteFilesVm.remotePath || "/")
                            var idx = p.lastIndexOf("/")
                            var parent = idx <= 0 ? "/" : p.substring(0, idx)
                            remoteFilesVm.changeRemotePath(parent || "/")
                        }
                    }

                    IconButton {
                        iconName: "mdi6.home-outline"
                        tooltip: "家目录"
                        enabled: pane.enabled
                        onClicked: remoteFilesVm.changeRemotePath("")
                    }

                    UiTextField {
                        id: pathField
                        dark: root.dark
                        text: remoteFilesVm.remotePath
                        Layout.fillWidth: true
                        onAccepted: remoteFilesVm.changeRemotePath(text)
                    }

                    IconButton {
                        iconName: "mdi6.arrow-right"
                        tooltip: "跳转"
                        enabled: pane.enabled
                        onClicked: remoteFilesVm.changeRemotePath(pathField.text)
                    }

                    IconButton {
                        iconName: "mdi6.upload"
                        tooltip: "上传文件"
                        enabled: pane.enabled
                        onClicked: uploadFileDialog.open()
                    }
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: 1
                    color: separator
                }
            }

            // Column header
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 26
                color: toolbarBg

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 14
                    spacing: 8

                    Label { text: ""; Layout.preferredWidth: 20 }
                    Label { text: "名称"; color: textMuted; font.pixelSize: 11; Layout.fillWidth: true }
                    Label { text: "修改时间"; color: textMuted; font.pixelSize: 11; Layout.preferredWidth: 132 }
                    Label { text: "大小"; color: textMuted; font.pixelSize: 11; Layout.preferredWidth: 86; horizontalAlignment: Text.AlignRight }
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: 1
                    color: separator
                }
            }

            // File list + drop
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                ListView {
                    id: fileList
                    anchors.fill: parent
                    clip: true
                    model: remoteFilesVm.remoteItems
                    delegate: Rectangle {
                        id: fileRow

                        required property var modelData
                        required property int index

                        width: ListView.view.width
                        height: 30
                        color: ListView.isCurrentItem ? selectedSoftBg : (fileMouse.containsMouse ? rowHover : (index % 2 === 0 ? surface : surfaceSubtle))

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 14
                            spacing: 8

                            UiIcon {
                                Layout.preferredWidth: 17
                                Layout.preferredHeight: 17
                                iconSize: 17
                                name: modelData.isDir ? "mdi6.folder" : "mdi6.file-outline"
                                color: modelData.isDir ? "#0A84FF" : textMuted
                            }

                            Label {
                                text: modelData.name || ""
                                color: textMain
                                font.pixelSize: 12
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }

                            Label {
                                text: root.formatModifiedTime(modelData.modifiedAt || 0)
                                color: textMuted
                                font.pixelSize: 11
                                Layout.preferredWidth: 132
                                elide: Text.ElideRight
                            }

                            Label {
                                text: modelData.isDir ? "" : root.formatSize(modelData.size || 0)
                                color: textMuted
                                font.pixelSize: 12
                                Layout.preferredWidth: 86
                                horizontalAlignment: Text.AlignRight
                            }
                        }

                        MouseArea {
                            id: fileMouse

                            anchors.fill: parent
                            hoverEnabled: true
                            acceptedButtons: Qt.LeftButton | Qt.RightButton
                            cursorShape: Qt.PointingHandCursor
                            onClicked: function(mouse) {
                                fileList.currentIndex = index
                                if (mouse.button === Qt.RightButton) {
                                    root.contextItem = modelData
                                    root.openPopupAtMouse(remoteFileMenu, fileMouse, mouse)
                                }
                            }
                            onDoubleClicked: {
                                if (modelData.isDir)
                                    remoteFilesVm.changeRemotePath(modelData.path || "")
                                else
                                    remoteFilesVm.editRemoteFile(modelData)
                            }
                        }
                    }

                    Label {
                        anchors.centerIn: parent
                        visible: pane.enabled && (remoteFilesVm.remoteItems || []).length === 0
                        text: "目录为空  ·  拖拽文件夹到此处即可上传"
                        color: textFaint
                        font.pixelSize: 12
                    }

                    Label {
                        anchors.centerIn: parent
                        visible: !pane.enabled
                        text: "请选择并连接远程主机"
                        color: textFaint
                        font.pixelSize: 12
                    }
                }

                MouseArea {
                    id: emptyAreaMouse
                    anchors.fill: parent
                    acceptedButtons: Qt.RightButton
                    propagateComposedEvents: true
                    onClicked: function(mouse) {
                        // empty-area right click -> menu without selection
                        var ix = fileList.indexAt(mouse.x, mouse.y + fileList.contentY)
                        if (ix < 0) {
                            root.contextItem = null
                            root.openPopupAtMouse(remoteFileMenu, emptyAreaMouse, mouse)
                        } else {
                            mouse.accepted = false
                        }
                    }
                }

                DropArea {
                    anchors.fill: parent
                    enabled: pane.enabled
                    onEntered: function(event) {
                        if (pane.acceptFileDrop(event)) {
                            dropOverlay.visible = true
                        }
                    }
                    onPositionChanged: function(event) {
                        if (pane.acceptFileDrop(event)) {
                            dropOverlay.visible = true
                        }
                    }
                    onExited: dropOverlay.visible = false
                    onDropped: function(event) {
                        dropOverlay.visible = false
                        if (!pane.acceptFileDrop(event))
                            return
                        var paths = []
                        var urls = event.urls || []
                        for (var i = 0; i < urls.length; i++)
                            paths.push(urls[i].toString())
                        if (paths.length > 0)
                            remoteFilesVm.uploadPaths(paths)
                        pane.acceptFileDrop(event)
                    }
                }

                Rectangle {
                    id: dropOverlay
                    anchors.fill: parent
                    anchors.margins: 6
                    visible: false
                    radius: 10
                    color: dark ? Qt.rgba(0.04, 0.52, 1.0, 0.18) : Qt.rgba(0.04, 0.52, 1.0, 0.12)
                    border.width: 2
                    border.color: selectedBg

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 24
                        anchors.rightMargin: 24
                        spacing: 8
                        UiIcon {
                            Layout.alignment: Qt.AlignHCenter
                            Layout.preferredWidth: 36
                            Layout.preferredHeight: 36
                            iconSize: 36
                            name: "mdi6.cloud-upload-outline"
                            color: selectedBg
                        }
                        Item { Layout.fillHeight: true }
                        Label {
                            Layout.alignment: Qt.AlignHCenter
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                            text: "释放以上传到 " + remoteFilesVm.remotePath
                            color: selectedBg
                            font.pixelSize: 13
                            font.weight: Font.DemiBold
                            elide: Text.ElideMiddle
                            wrapMode: Text.NoWrap
                        }
                        Item { Layout.fillHeight: true }
                    }
                }
            }
        }
    }

    component TerminalPane: Rectangle {
        id: terminalPane
        property var bridge: null
        color: dark ? "#101014" : "#FFFFFF"

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 42
                color: toolbarBg

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 12
                    spacing: 10

                    UiIcon {
                        Layout.preferredWidth: 14
                        Layout.preferredHeight: 14
                        iconSize: 14
                        name: "mdi6.console-line"
                        color: root.sftpConnected ? success : textMuted
                    }

                    Label {
                        text: "SSH 终端"
                        color: textMain
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                    }

                    Label {
                        text: root.sftpConnected ? "就绪" : "未连接 SFTP"
                        color: root.sftpConnected ? success : textFaint
                        font.pixelSize: 11
                    }

                    Item { Layout.fillWidth: true }

                    IconButton {
                        iconName: "mdi6.play"
                        tooltip: "打开终端"
                        enabled: root.sftpConnected
                        onClicked: remoteFilesVm.openTerminal()
                    }

                    IconButton {
                        iconName: "mdi6.stop"
                        tooltip: "关闭终端"
                        enabled: root.sftpConnected
                        onClicked: remoteFilesVm.closeTerminal()
                    }
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: 1
                    color: separator
                }
            }

            QtObject {
                id: terminalProxy
                WebChannel.id: "remoteTerminalBridge"
                signal output(string text)
                signal closed(string message)
                function sendInput(text) {
                    if (terminalPane.bridge) terminalPane.bridge.sendInput(text)
                }
                function resize(cols, rows) {
                    if (terminalPane.bridge) terminalPane.bridge.resize(cols, rows)
                }
            }

            Connections {
                target: terminalPane.bridge
                ignoreUnknownSignals: true
                function onOutput(text) { terminalProxy.output(text) }
                function onClosed(message) { terminalProxy.closed(message) }
            }

            WebChannel {
                id: terminalChannel
                registeredObjects: [terminalProxy]
            }

            WebEngineView {
                id: terminalView
                Layout.fillWidth: true
                Layout.fillHeight: true
                url: Qt.resolvedUrl("assets/terminal.html")
                webChannel: terminalChannel
                onNavigationRequested: function(request) {
                    if (request.url.toString().indexOf(Qt.resolvedUrl("assets/terminal.html").toString()) !== 0)
                        request.action = WebEngineNavigationRequest.IgnoreRequest
                }
                onContextMenuRequested: function(request) {
                    request.accepted = true
                    webContextMenu.editFlags = request.editFlags
                    webContextMenu.hasSelection = (request.selectedText || "").length > 0
                    webContextMenu.openAt(terminalView, request.position.x, request.position.y)
                }
            }

            UiMenuPopup {
                id: webContextMenu
                width: 200
                dark: root.dark
                property int editFlags: 0
                property bool hasSelection: false
                readonly property int flagCanUndo: 0x1
                readonly property int flagCanRedo: 0x2
                readonly property int flagCanCut: 0x4
                readonly property int flagCanCopy: 0x8
                readonly property int flagCanPaste: 0x10
                readonly property int flagCanSelectAll: 0x40

                contentItem: Column {
                    id: webContextMenuColumn
                    spacing: 0

                    UiMenuItem {
                        width: webContextMenu.width - 8
                        dark: root.dark
                        text: "撤销"
                        itemEnabled: (webContextMenu.editFlags & webContextMenu.flagCanUndo) !== 0
                        onTriggered: { terminalView.triggerWebAction(WebEngineView.Undo); webContextMenu.close() }
                    }
                    UiMenuItem {
                        width: webContextMenu.width - 8
                        dark: root.dark
                        text: "重做"
                        itemEnabled: (webContextMenu.editFlags & webContextMenu.flagCanRedo) !== 0
                        onTriggered: { terminalView.triggerWebAction(WebEngineView.Redo); webContextMenu.close() }
                    }
                    UiMenuSeparator { width: webContextMenu.width - 8; dark: root.dark }
                    UiMenuItem {
                        width: webContextMenu.width - 8
                        dark: root.dark
                        text: "剪切"
                        itemEnabled: (webContextMenu.editFlags & webContextMenu.flagCanCut) !== 0
                        onTriggered: { terminalView.triggerWebAction(WebEngineView.Cut); webContextMenu.close() }
                    }
                    UiMenuItem {
                        width: webContextMenu.width - 8
                        dark: root.dark
                        text: "复制"
                        itemEnabled: (webContextMenu.editFlags & webContextMenu.flagCanCopy) !== 0
                        onTriggered: { terminalView.triggerWebAction(WebEngineView.Copy); webContextMenu.close() }
                    }
                    UiMenuItem {
                        width: webContextMenu.width - 8
                        dark: root.dark
                        text: "粘贴"
                        itemEnabled: (webContextMenu.editFlags & webContextMenu.flagCanPaste) !== 0
                        onTriggered: { terminalView.triggerWebAction(WebEngineView.Paste); webContextMenu.close() }
                    }
                    UiMenuSeparator { width: webContextMenu.width - 8; dark: root.dark }
                    UiMenuItem {
                        width: webContextMenu.width - 8
                        dark: root.dark
                        text: "全选"
                        itemEnabled: (webContextMenu.editFlags & webContextMenu.flagCanSelectAll) !== 0
                        onTriggered: { terminalView.triggerWebAction(WebEngineView.SelectAll); webContextMenu.close() }
                    }
                }
            }
        }
    }

    component FtpLogPane: Rectangle {
        id: ftpPane
        color: dark ? "#0E1014" : "#0B0F19"

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 42
                color: toolbarBg

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 12
                    spacing: 10

                    UiIcon {
                        Layout.preferredWidth: 14
                        Layout.preferredHeight: 14
                        iconSize: 14
                        name: "mdi6.text-box-outline"
                        color: success
                    }

                    Label {
                        text: "FTP 命令日志"
                        color: textMain
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                    }

                    Label {
                        text: (remoteFilesVm.ftpLog || []).length + " 条"
                        color: textFaint
                        font.pixelSize: 11
                    }

                    Item { Layout.fillWidth: true }

                    PushButton {
                        label: "复制全部"
                        iconName: "mdi6.content-copy"
                        enabled: (remoteFilesVm.ftpLog || []).length > 0
                        onClicked: remoteFilesVm.copyFtpLog()
                    }

                    PushButton {
                        label: "清空"
                        iconName: "mdi6.broom"
                        enabled: (remoteFilesVm.ftpLog || []).length > 0
                        onClicked: remoteFilesVm.clearFtpLog()
                    }
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: 1
                    color: separator
                }
            }

            ScrollView {
                id: ftpLogScroll
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AsNeeded
                ScrollBar.vertical.policy: ScrollBar.AsNeeded

                ListView {
                    id: ftpLogList
                    width: ftpLogScroll.availableWidth
                    spacing: 0
                    model: remoteFilesVm.ftpLog || []
                    interactive: true
                    boundsBehavior: Flickable.StopAtBounds
                    onCountChanged: positionViewAtEnd()
                    delegate: Item {
                        id: ftpLogRow
                        required property string modelData

                        width: ftpLogList.width
                        height: lineLabel.implicitHeight + 4

                        MouseArea {
                            anchors.fill: parent
                            acceptedButtons: Qt.RightButton
                            onClicked: function(mouse) {
                                if (mouse.button !== Qt.RightButton)
                                    return
                                ftpLogMenu.lineText = ftpLogRow.modelData || ""
                                ftpLogMenu.openAt(ftpLogRow, mouse.x, mouse.y)
                            }
                        }

                        Label {
                            id: lineLabel
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.leftMargin: 14
                            anchors.rightMargin: 14
                            anchors.verticalCenter: parent.verticalCenter
                            text: ftpLogRow.modelData
                            color: {
                                var t = String(ftpLogRow.modelData || "")
                                if (t.indexOf("*cmd*") >= 0) return "#7CB7FF"
                                if (t.indexOf("*resp*") >= 0) return "#A5E3A1"
                                if (t.indexOf("fallback to LIST") >= 0) return "#A5E3A1"
                                return dark ? "#D6D8E1" : "#E0E3EA"
                            }
                            font.family: "SF Mono, Menlo, Consolas, monospace"
                            font.pixelSize: 12
                            wrapMode: Text.NoWrap
                            elide: Text.ElideRight
                        }
                    }
                }
            }

            UiMenuPopup {
                id: ftpLogMenu
                width: 200
                dark: root.dark
                property string lineText: ""

                contentItem: Column {
                    id: ftpLogMenuColumn
                    spacing: 0

                    UiMenuItem {
                        width: ftpLogMenu.width - 8
                        dark: root.dark
                        text: "复制当前行"
                        itemEnabled: ftpLogMenu.lineText.length > 0
                        onTriggered: { remoteFilesVm.copyFtpLogLine(ftpLogMenu.lineText); ftpLogMenu.close() }
                    }
                    UiMenuItem {
                        width: ftpLogMenu.width - 8
                        dark: root.dark
                        text: "复制全部"
                        itemEnabled: (remoteFilesVm.ftpLog || []).length > 0
                        onTriggered: { remoteFilesVm.copyFtpLog(); ftpLogMenu.close() }
                    }
                }
            }
        }
    }

    component IconButton: UiIconButton {
        id: control

        property bool dangerRole: false

        dark: root.dark
        danger: dangerRole
        controlSize: 28
    }

    component PushButton: UiButton {
        id: control

        property string label: ""
        property bool accent: false
        property bool dangerRole: false

        dark: root.dark
        text: label
        variant: accent ? "primary" : "secondary"
        danger: dangerRole
        font.pixelSize: 12
    }
}
