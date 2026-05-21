pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import "../theme"

ComboBox {
    id: control

    property bool dark: false
    property int cornerRadius: Theme.radii.md
    property bool flatStyle: false
    property color fillColor: control.dark
        ? Theme.token("color-bg-elevated", true)
        : "#FFFFFF"
    property color hoverFillColor: control.dark
        ? Theme.token("color-bg-subtle", true)
        : Theme.token("color-bg-subtle-2", false)
    property color textColor: Theme.token("color-text-primary", control.dark)
    property color mutedColor: Theme.token("color-text-regular", control.dark)
    property color accentColor: Theme.token("color-primary-active", control.dark)
    property var itemColorFn: null

    implicitHeight: 30
    leftPadding: 12
    rightPadding: control.flatStyle ? 24 : 34
    hoverEnabled: true
    font.family: Theme.fontFamily.ui
    font.pixelSize: 13

    palette.buttonText: control.textColor
    palette.text: control.textColor

    contentItem: Text {
        text: control.displayText
        color: control.textColor
        font: control.font
        verticalAlignment: Text.AlignVCenter
        horizontalAlignment: Text.AlignLeft
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: control.cornerRadius
        color: control.down || control.hovered ? control.hoverFillColor : control.fillColor
        border.width: 1
        border.color: {
            if (control.activeFocus)
                return Qt.rgba(control.accentColor.r, control.accentColor.g, control.accentColor.b, control.dark ? 0.72 : 0.58)
            if (control.hovered || control.down)
                return Theme.token("color-border-strong", control.dark)
            return Theme.token("color-border-default", control.dark)
        }
        antialiasing: true

        Behavior on color { ColorAnimation { duration: 100 } }
        Behavior on border.color { ColorAnimation { duration: 100 } }
    }

    indicator: Item {
        width: control.flatStyle ? 20 : 28
        height: control.height
        x: control.width - width - 4
        y: 0

        Rectangle {
            anchors.centerIn: parent
            width: control.flatStyle ? 18 : 22
            height: control.flatStyle ? 18 : 22
            radius: 6
            color: {
                if (control.flatStyle)
                    return "transparent"
                if (control.down)
                    return Theme.token("color-bg-subtle", control.dark)
                if (control.hovered || control.activeFocus)
                    return control.dark ? Qt.rgba(1, 1, 1, 0.06) : Qt.rgba(0, 0, 0, 0.045)
                return "transparent"
            }
        }

        Canvas {
            id: chevron
            anchors.centerIn: parent
            width: 10
            height: 8
            contextType: "2d"

            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            Component.onCompleted: requestPaint()

            Connections {
                target: control
                function onPressedChanged() { chevron.requestPaint() }
                function onHoveredChanged() { chevron.requestPaint() }
                function onActiveFocusChanged() { chevron.requestPaint() }
            }

            onPaint: {
                var ctx = context
                ctx.reset()
                ctx.lineWidth = 1.6
                ctx.lineCap = "round"
                ctx.lineJoin = "round"
                ctx.strokeStyle = control.activeFocus || control.down
                    ? control.accentColor
                    : Theme.token("color-text-secondary", control.dark)

                var w = width
                var h = height
                var cx = w / 2
                var cy = h / 2
                var halfW = 3.6
                var halfH = 2.2
                ctx.beginPath()
                ctx.moveTo(cx - halfW, cy - halfH)
                ctx.lineTo(cx, cy + halfH)
                ctx.lineTo(cx + halfW, cy - halfH)
                ctx.stroke()
            }
        }
    }

    popup: Popup {
        y: control.height + 4
        width: Math.max(control.width, 140)
        padding: 4
        implicitHeight: Math.min(popupList.contentHeight + 8, 320)

        enter: Transition {
            ParallelAnimation {
                NumberAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: 80; easing.type: Easing.OutCubic }
                NumberAnimation { property: "scale"; from: 0.98; to: 1.0; duration: 80; easing.type: Easing.OutCubic }
            }
        }

        contentItem: ListView {
            id: popupList
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            spacing: 0
        }

        background: UiMenuSurface {
            dark: control.dark
            radius: 8
        }
    }

    delegate: UiMenuItem {
        id: optionDelegate
        required property int index
        required property var modelData

        width: (control.popup ? control.popup.width : control.width) - 8
        dark: control.dark
        reserveCheckSpace: true
        checked: control.currentIndex === index
        highlighted: control.highlightedIndex === index
        text: typeof modelData === "object" && modelData !== null && control.textRole.length > 0
            ? ("" + (modelData[control.textRole] ?? ""))
            : ("" + modelData)
        textColorOverride: {
            if (!control.itemColorFn) return "transparent"
            var c = control.itemColorFn(optionDelegate.index, optionDelegate.modelData)
            return c ? c : "transparent"
        }
        onTriggered: {
            control.currentIndex = index
            control.popup.close()
        }
    }
}
