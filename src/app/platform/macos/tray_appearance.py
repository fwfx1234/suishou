from __future__ import annotations


_PACKAGED_COLOR = "#FFFFFF"
_DEV_COLOR = "#8B5CF6"


class MacOSTrayAppearance:
    def icon_color(self, *, packaged: bool) -> str:
        return _PACKAGED_COLOR if packaged else _DEV_COLOR

    def apply_mask(self, icon: object, *, packaged: bool) -> None:
        if not packaged:
            return
        set_mask = getattr(icon, "setIsMask", None)
        if callable(set_mask):
            set_mask(True)
