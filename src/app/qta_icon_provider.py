from __future__ import annotations

from dataclasses import dataclass
from collections import OrderedDict

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtQuick import QQuickImageProvider


_qtawesome = None
_qtawesome_loaded = False


def _load_qtawesome():
    global _qtawesome, _qtawesome_loaded
    if _qtawesome_loaded:
        return _qtawesome
    _qtawesome_loaded = True
    try:
        import qtawesome as qta
        _qtawesome = qta
    except Exception:  # pragma: no cover - runtime fallback
        _qtawesome = None
    return _qtawesome


@dataclass
class IconRequest:
    name: str
    color: QColor
    size: int


class QtAwesomeImageProvider(QQuickImageProvider):
    """Expose qtawesome icons to QML via image://qta/... URLs."""

    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Pixmap)
        self._cache: OrderedDict[tuple[str, str, int], QPixmap] = OrderedDict()
        self._cache_limit = 256

    def requestPixmap(self, icon_id: str, size: QSize, requestedSize: QSize) -> QPixmap:
        spec = self._parse(icon_id, requestedSize)
        key = (spec.name, spec.color.name(QColor.NameFormat.HexArgb), spec.size)
        cached = self._cache.get(key)
        if cached is not None:
            self._cache.move_to_end(key)
            if size is not None:
                size.setWidth(cached.width())
                size.setHeight(cached.height())
            return QPixmap(cached)

        qta = _load_qtawesome()
        if qta is None:
            return QPixmap(spec.size, spec.size)

        try:
            icon = qta.icon(spec.name, color=spec.color)
            pixmap = icon.pixmap(spec.size, spec.size)
        except Exception:
            # Never crash QML image loading for invalid icon ids.
            pixmap = QPixmap(spec.size, spec.size)
            pixmap.fill(QColor(0, 0, 0, 0))
        self._cache[key] = QPixmap(pixmap)
        self._cache.move_to_end(key)
        while len(self._cache) > self._cache_limit:
            self._cache.popitem(last=False)
        if size is not None:
            size.setWidth(pixmap.width())
            size.setHeight(pixmap.height())
        return pixmap

    def _parse(self, icon_id: str, requested_size: QSize) -> IconRequest:
        parts = [segment for segment in icon_id.split(";") if segment]
        icon_name = parts[0] if parts else "mdi6.help-circle-outline"
        color = QColor("#64748B")
        pixel_size = 16

        if requested_size.isValid():
            pixel_size = max(requested_size.width(), requested_size.height(), pixel_size)

        for segment in parts[1:]:
            if "=" not in segment:
                continue
            key, value = segment.split("=", 1)
            if key == "color":
                if value and not value.startswith("#"):
                    value = "#" + value
                parsed = QColor(value)
                if parsed.isValid():
                    color = parsed
            elif key == "size":
                try:
                    pixel_size = max(8, int(value))
                except ValueError:
                    pass

        return IconRequest(icon_name, color, pixel_size)
