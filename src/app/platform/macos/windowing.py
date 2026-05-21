from __future__ import annotations

from ctypes import c_void_p


class MacOSWindowingApi:
    def configure_launcher_window(self, window: object) -> bool:
        return self.configure_overlay_window(window, force_top=True)

    def configure_overlay_window(self, window: object, *, force_top: bool = True) -> bool:
        ns_window = self._ns_window(window)
        if ns_window is None:
            return False
        try:
            import AppKit  # type: ignore

            behavior = int(ns_window.collectionBehavior())
            for name in (
                "NSWindowCollectionBehaviorCanJoinAllSpaces",
                "NSWindowCollectionBehaviorFullScreenAuxiliary",
                "NSWindowCollectionBehaviorIgnoresCycle",
            ):
                behavior |= int(getattr(AppKit, name, 0))
            ns_window.setCollectionBehavior_(behavior)
            if force_top:
                ns_window.setLevel_(self._overlay_window_level(AppKit))
            ns_window.setHidesOnDeactivate_(False)
            return True
        except Exception:
            return False

    def activate_window(self, window: object | None = None) -> bool:
        activated = False
        try:
            import AppKit  # type: ignore

            app = AppKit.NSApplication.sharedApplication()
            app.activateIgnoringOtherApps_(True)
            activated = True
        except Exception:
            activated = False
        ns_window = self._ns_window(window) if window is not None else None
        if ns_window is not None:
            try:
                ns_window.orderFrontRegardless()
                ns_window.makeKeyAndOrderFront_(None)
                activated = True
            except Exception:
                pass
        return activated

    def focused_window_center(self) -> tuple[int, int] | None:
        try:
            import AppKit  # type: ignore
            import Quartz  # type: ignore

            app = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()
            if app is None:
                return None
            pid = int(app.processIdentifier())
            options = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
            windows = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID) or []
            for window in windows:
                if int(window.get("kCGWindowOwnerPID", -1)) != pid:
                    continue
                if int(window.get("kCGWindowLayer", 0)) != 0:
                    continue
                if float(window.get("kCGWindowAlpha", 1.0) or 0.0) <= 0.0:
                    continue
                bounds = window.get("kCGWindowBounds") or {}
                x = float(bounds.get("X", 0.0))
                y = float(bounds.get("Y", 0.0))
                width = float(bounds.get("Width", 0.0))
                height = float(bounds.get("Height", 0.0))
                if width <= 1.0 or height <= 1.0:
                    continue
                return round(x + width / 2.0), round(y + height / 2.0)
        except Exception:
            return None
        return None

    @staticmethod
    def _overlay_window_level(appkit: object) -> int:
        for name in (
            "NSScreenSaverWindowLevel",
            "NSMainMenuWindowLevel",
            "NSStatusWindowLevel",
            "NSModalPanelWindowLevel",
            "NSFloatingWindowLevel",
        ):
            value = getattr(appkit, name, None)
            if value is not None:
                return int(value)
        return 1000

    @staticmethod
    def _ns_window(window: object | None) -> object | None:
        if window is None:
            return None
        try:
            import objc  # type: ignore

            native_id = int(window.winId())
            if not native_id:
                return None
            native_obj = objc.objc_object(c_void_p=native_id)
            if hasattr(native_obj, "setCollectionBehavior_"):
                return native_obj
            get_window = getattr(native_obj, "window", None)
            if callable(get_window):
                return get_window()
        except Exception:
            return None
        return None


# Backwards-compatible module-level functions (旧代码路径 import 时仍然可用)。
_default_api = MacOSWindowingApi()


def configure_launcher_window(window: object) -> bool:
    return _default_api.configure_launcher_window(window)


def configure_overlay_window(window: object, *, force_top: bool = True) -> bool:
    return _default_api.configure_overlay_window(window, force_top=force_top)


def activate_window(window: object | None = None) -> bool:
    return _default_api.activate_window(window)


def focused_window_center() -> tuple[int, int] | None:
    return _default_api.focused_window_center()
