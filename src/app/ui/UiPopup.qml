import QtQuick
import QtQuick.Controls
import "../theme"

Popup {
    id: root

    property bool dark: false
    property int surfaceRadius: Theme.radii.lg
    property color surfaceFillColor: Theme.token("color-bg-surface", root.dark)
    property int surfaceBorderWidth: 1
    property color surfaceBorderColor: root.dark ? Qt.rgba(1, 1, 1, 0.10) : Qt.rgba(0, 0, 0, 0.08)

    parent: Overlay.overlay
    padding: 0
    modal: false
    focus: true
    closePolicy: Popup.CloseOnPressOutside | Popup.CloseOnEscape

    enter: Transition {
        ParallelAnimation {
            NumberAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: 80; easing.type: Easing.OutCubic }
            NumberAnimation { property: "scale"; from: 0.98; to: 1.0; duration: 80; easing.type: Easing.OutCubic }
        }
    }

    background: UiPopupSurface {
        dark: root.dark
        radius: root.surfaceRadius
        fillColor: root.surfaceFillColor
        borderWidth: root.surfaceBorderWidth
        borderColor: root.surfaceBorderColor
    }

    function clampToOverlay(preferredX, preferredY) {
        var overlay = Overlay.overlay
        if (!overlay)
            return { x: preferredX, y: preferredY }
        var margin = 4
        var w = root.width || root.implicitWidth || 0
        var h = root.height || root.implicitHeight || 0
        var maxX = Math.max(margin, overlay.width - w - margin)
        var maxY = Math.max(margin, overlay.height - h - margin)
        return {
            x: Math.max(margin, Math.min(preferredX, maxX)),
            y: Math.max(margin, Math.min(preferredY, maxY))
        }
    }

    function openAt(srcItem, x, y) {
        var overlay = Overlay.overlay
        var p = overlay && srcItem ? srcItem.mapToItem(overlay, x, y) : { x: x, y: y }
        var pos = clampToOverlay(p.x, p.y)
        root.x = pos.x
        root.y = pos.y
        root.open()
        Qt.callLater(function() {
            if (!root.opened)
                return
            var adjusted = clampToOverlay(root.x, root.y)
            root.x = adjusted.x
            root.y = adjusted.y
        })
    }

    function openCentered() {
        var overlay = Overlay.overlay
        if (overlay) {
            root.x = Math.max(0, (overlay.width - root.width) / 2)
            root.y = Math.max(0, (overlay.height - root.height) / 2)
        }
        root.open()
    }
}
