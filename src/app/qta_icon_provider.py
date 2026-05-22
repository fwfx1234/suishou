"""QML image://qta/<icon-id> provider backed by pre-rendered PNG assets.

To avoid the ~45 MB qtawesome font cache at startup, icons used in the app are
baked to ``assets/qta_icons/<set>.<name>.png`` by ``tools/gen_qta_icons.py``.
The provider loads each PNG once into a cache, then tints + scales on demand.

When an icon id isn't present on disk, we fall back to qtawesome (lazy import).
This keeps the dev workflow ergonomic: drop a new ``qta:foo.bar`` reference,
restart, and it still renders. Re-run the generator before shipping.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtQuick import QQuickImageProvider


@dataclass
class IconRequest:
    name: str
    color: QColor
    size: int


def _default_assets_dir() -> Path:
    """Locate assets/qta_icons whether running from source or a PyInstaller bundle."""

    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", ""))
        candidate = meipass / "assets" / "qta_icons"
        if candidate.is_dir():
            return candidate
    return Path(__file__).resolve().parents[2] / "assets" / "qta_icons"


class QtAwesomeImageProvider(QQuickImageProvider):
    """Expose qtawesome icons to QML via image://qta/... URLs."""

    def __init__(self, assets_dir: Path | None = None) -> None:
        super().__init__(QQuickImageProvider.ImageType.Pixmap)
        self._assets_dir = assets_dir or _default_assets_dir()
        self._cache: dict[str, QImage | None] = {}
        self._lock = Lock()
        self._qta_warned = False

    def requestPixmap(self, icon_id: str, size: QSize, requestedSize: QSize) -> QPixmap:
        spec = self._parse(icon_id, requestedSize)
        mask = self._load_mask(spec.name)
        if mask is None or mask.isNull():
            pixmap = QPixmap(spec.size, spec.size)
            pixmap.fill(Qt.GlobalColor.transparent)
        else:
            pixmap = self._colorize_and_scale(mask, spec.color, spec.size)
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

    def _load_mask(self, icon_name: str) -> QImage | None:
        with self._lock:
            if icon_name in self._cache:
                return self._cache[icon_name]
        path = self._assets_dir / f"{icon_name}.png"
        image: QImage | None = None
        if path.is_file():
            loaded = QImage(str(path))
            if not loaded.isNull():
                if loaded.format() != QImage.Format.Format_ARGB32_Premultiplied:
                    loaded = loaded.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
                image = loaded
        if image is None:
            image = self._fallback_via_qtawesome(icon_name)
        with self._lock:
            self._cache[icon_name] = image
        return image

    def _fallback_via_qtawesome(self, icon_name: str) -> QImage | None:
        """Dev-only fallback. Loads qtawesome on first miss, never on startup."""

        try:
            import qtawesome  # noqa: PLC0415
        except Exception:
            return None
        if not self._qta_warned:
            self._qta_warned = True
            try:
                from app.logging import get_logger

                get_logger("app.qta_icon_provider").warning(
                    "qta.icon.fallback",
                    "qtawesome 回退加载（请运行 tools/gen_qta_icons.py 烘焙）",
                    icon=icon_name,
                )
            except Exception:
                pass
        try:
            icon = qtawesome.icon(icon_name, color=QColor("#000000"))
            pixmap = icon.pixmap(QSize(256, 256))
            image = pixmap.toImage()
            if image.isNull():
                return None
            return image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        except Exception:
            return None

    @staticmethod
    def _colorize_and_scale(mask: QImage, color: QColor, target_px: int) -> QPixmap:
        if target_px <= 0:
            target_px = mask.width()
        scaled = mask.scaled(
            target_px,
            target_px,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        result = QImage(target_px, target_px, QImage.Format.Format_ARGB32_Premultiplied)
        result.fill(Qt.GlobalColor.transparent)
        painter = QPainter(result)
        x = max(0, (target_px - scaled.width()) // 2)
        y = max(0, (target_px - scaled.height()) // 2)
        painter.drawImage(x, y, scaled)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(x, y, scaled.width(), scaled.height(), color)
        painter.end()
        return QPixmap.fromImage(result)


_shared_provider: QtAwesomeImageProvider | None = None
_shared_provider_lock = Lock()


def _provider() -> QtAwesomeImageProvider:
    global _shared_provider
    with _shared_provider_lock:
        if _shared_provider is None:
            _shared_provider = QtAwesomeImageProvider()
        return _shared_provider


def load_icon(icon_name: str, color: QColor | str = "#64748B", size: int = 64) -> QPixmap | None:
    """Convenience helper for Python-side icon loading (e.g. system tray).

    Returns ``None`` if neither the baked PNG nor qtawesome can satisfy the request.
    """

    provider = _provider()
    mask = provider._load_mask(icon_name)
    if mask is None or mask.isNull():
        return None
    color_obj = color if isinstance(color, QColor) else QColor(color)
    return provider._colorize_and_scale(mask, color_obj, size)
