pragma Singleton
import QtQuick

QtObject {
    readonly property var colors: ({
        slate: { 50: "#F8FAFC", 100: "#F1F5F9", 200: "#E2E8F0", 400: "#94A3B8", 500: "#64748B", 600: "#475569", 700: "#334155", 800: "#1E293B", 900: "#0F172A" },
        blue: { 50: "#EFF6FF", 100: "#DBEAFE", 200: "#BFDBFE", 300: "#93C5FD", 400: "#60A5FA", 500: "#0A84FF", 600: "#007AFF", 700: "#0066CC" },
        violet: { 50: "#F5F3FF", 100: "#EDE9FE", 300: "#C4B5FD", 500: "#8B5CF6", 600: "#7C3AED", 700: "#6D28D9" },
        green: { 500: "#16A34A", 600: "#10B981" },
        amber: { 500: "#F59E0B", 600: "#D97706" },
        red: { 500: "#EF4444", 600: "#DC2626" },
        cyan: { 500: "#0EA5E9" },
        white: "#FFFFFF"
    })

    readonly property var space: ({ "0.5": 2, "1": 4, "1.5": 6, "2": 8, "2.5": 10, "3": 12, "4": 16, "5": 20, "6": 24 })
    readonly property var radii: ({ xs: 4, sm: 6, md: 8, lg: 10, xl: 12 })
    readonly property var fontFamily: ({
        ui: Qt.application.font.family,
        mono: Qt.platform.os === "osx" ? "Menlo" : "Consolas"
    })
    readonly property var fontSize: ({ title: 20, heading: 15, body: 13, mono: 12, nav: 13, caption: 11 })

    readonly property var tokensLight: ({
        "color-bg-page": "#F5F6F8",
        "color-bg-surface": "#FFFFFF",
        "color-bg-elevated": "#FFFFFF",
        "color-bg-subtle": "#EEF1F5",
        "color-bg-subtle-2": "#F8F9FB",
        "color-border-default": "#D7DCE5",
        "color-border-strong": "#B8C0CC",
        "color-text-primary": "#1D1D1F",
        "color-text-regular": "#3A3A3C",
        "color-text-secondary": "#8A8F98",
        "color-text-placeholder": "#A5ACB8",
        "color-primary": "#0A84FF",
        "color-primary-hover": "#3398FF",
        "color-primary-active": "#007AFF",
        "color-primary-bg": "#E8F3FF",
        "color-primary-soft": "#D6E9FF",
        "color-success": "#10B981",
        "color-warning": "#F59E0B",
        "color-danger": "#FF3B30",
        "color-info": "#0EA5E9",
        "color-nav-idle": "#334155",
        "color-nav-active-bg": "#D6E9FF",
        "color-nav-item-active-bg": "#E8F3FF",
        "color-nav-active-text": "#0066CC",
        "color-nav-icon-idle-bg": "#F1F5F9",
        "color-nav-icon-active-bg": "#0A84FF",
        "color-nav-icon-active-bg-soft": "#D6E9FF",
        "color-method-get": "#16A34A",
        "color-method-post": "#F59E0B",
        "color-method-put": "#3B82F6",
        "color-method-delete": "#EF4444",
        "color-method-patch": "#0EA5E9",
        "color-table-header": "#FAFAFB",
        "color-row-hover": "#EEF4FB",
        "color-row-selected": "#DDEEFF",
        "color-status-bar-bg": "#F7F8FA",
        "color-shadow": "#000000"
    })

    readonly property var tokensDark: ({
        "color-bg-page": "#101216",
        "color-bg-surface": "#1B1E24",
        "color-bg-elevated": "#242830",
        "color-bg-subtle": "#252A33",
        "color-bg-subtle-2": "#181B21",
        "color-border-default": "#3A414D",
        "color-border-strong": "#596171",
        "color-text-primary": "#F5F5F7",
        "color-text-regular": "#D8DCE3",
        "color-text-secondary": "#989FAA",
        "color-text-placeholder": "#7F8793",
        "color-primary": "#0A84FF",
        "color-primary-hover": "#3398FF",
        "color-primary-active": "#0A84FF",
        "color-primary-bg": "#0D2A45",
        "color-primary-soft": "#143B5F",
        "color-success": "#10B981",
        "color-warning": "#F59E0B",
        "color-danger": "#FF453A",
        "color-info": "#0EA5E9",
        "color-nav-idle": "#94A3B8",
        "color-nav-active-bg": "#0A84FF",
        "color-nav-item-active-bg": "#0D2A45",
        "color-nav-active-text": "#E8F3FF",
        "color-nav-icon-idle-bg": "#242A34",
        "color-nav-icon-active-bg": "#0A84FF",
        "color-nav-icon-active-bg-soft": "#143B5F",
        "color-method-get": "#22C55E",
        "color-method-post": "#FBBF24",
        "color-method-put": "#60A5FA",
        "color-method-delete": "#F87171",
        "color-method-patch": "#22D3EE",
        "color-table-header": "#0F1623",
        "color-row-hover": "#222A35",
        "color-row-selected": "#143B5F",
        "color-status-bar-bg": "#171B22",
        "color-shadow": "#000000"
    })

    function token(name, darkMode) {
        return (darkMode ? tokensDark : tokensLight)[name]
    }
}
