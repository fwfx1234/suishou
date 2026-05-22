import QtQuick
import "../../../app/ui"
import "../../../app/theme"

Rectangle {
    id: root

    property bool dark: false
    property color panelBg: "#FFFFFF"
    property color textMain: "#333333"
    property color textMuted: "#666666"
    property int currentTab: 0
    property var tabCounts: []
    property var tabModel: [
        { title: "Params", icon: "mdi6.tune-variant" },
        { title: "Path", icon: "mdi6.link-variant" },
        { title: "Body", icon: "mdi6.code-json" },
        { title: "Headers", icon: "mdi6.format-header-pound" },
        { title: "Cookies", icon: "mdi6.cookie-outline" },
        { title: "Auth", icon: "mdi6.shield-key-outline" },
        { title: "Pre", icon: "mdi6.playlist-edit" },
        { title: "Assert", icon: "mdi6.check-decagram-outline" },
        { title: "Tools", icon: "mdi6.history" }
    ]

    signal tabChanged(int index)

    function countAt(index) {
        if (!root.tabCounts || index < 0 || index >= root.tabCounts.length)
            return 0
        var value = Number(root.tabCounts[index])
        return isNaN(value) ? 0 : value
    }

    color: root.panelBg

    UiSegmentedTabs {
        anchors.fill: parent
        anchors.leftMargin: Theme.space["2"]
        anchors.rightMargin: Theme.space["2"]
        dark: root.dark
        tabs: root.tabModel
        counts: root.tabCounts
        currentIndex: root.currentTab
        minItemWidth: 58
        itemPaddingX: Theme.space["2"]
        controlHeight: 28
        textColor: root.textMain
        mutedColor: root.textMuted
        onActivated: function(index) { root.tabChanged(index) }
    }
}
