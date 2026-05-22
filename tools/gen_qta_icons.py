"""Scan the codebase for qtawesome icon ids and bake each one to a PNG asset.

Output goes to ``assets/qta_icons/<set>.<name>.png`` — single black silhouette
with alpha mask, 256×256. Runtime renders these via QtAwesomeImageProvider
without ever importing qtawesome on startup.

Usage: ``uv run python tools/gen_qta_icons.py``
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT_DIR = ROOT / "assets" / "qta_icons"
ICON_SIZE = 256
RENDER_COLOR = "#000000"

ICON_NAME_PATTERN = re.compile(
    r"\b(?:mdi6|fa5s|fa5r|fa5b|fa6s|fa6r|fa6b|ei|ri|msc|ph|mdi|fa|fa5)\.[a-zA-Z0-9_-]+\b"
)


def collect_icon_names() -> set[str]:
    names: set[str] = set()
    for path in SRC.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".qml", ".py", ".json"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in ICON_NAME_PATTERN.findall(text):
            if _placeholder_icon_name(match):
                continue
            names.add(match)
    # Plugin manifests sometimes declare `icon: "qta:..."`; covered by regex above.
    return names


def _placeholder_icon_name(name: str) -> bool:
    return name == "foo.bar" or all(char == "." for char in name)


def safe_filename(icon_name: str) -> str:
    # icon_name like "mdi6.api" → "mdi6.api.png" (already filesystem-safe)
    return f"{icon_name}.png"


def main() -> int:
    from PySide6.QtCore import QSize, Qt
    from PySide6.QtGui import QColor, QImage, QPainter
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)

    import qtawesome as qta

    icon_names = sorted(collect_icon_names())
    if not icon_names:
        print("no qta icon references found under src/", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict[str, int]] = {}
    written = 0
    skipped: list[str] = []
    color = QColor(RENDER_COLOR)

    for name in icon_names:
        out_path = OUT_DIR / safe_filename(name)
        try:
            icon = qta.icon(name, color=color)
            pixmap = icon.pixmap(QSize(ICON_SIZE, ICON_SIZE))
            image = pixmap.toImage()
            if image.isNull() or image.size().width() == 0:
                skipped.append(name)
                continue
            # Normalize to ARGB32 so QImage.loadFromData / colorize is predictable.
            if image.format() != QImage.Format.Format_ARGB32_Premultiplied:
                image = image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
            if not image.save(str(out_path), "PNG"):
                skipped.append(name)
                continue
            manifest[name] = {"width": image.width(), "height": image.height()}
            written += 1
        except Exception as exc:  # pragma: no cover - dev script
            skipped.append(f"{name} ({exc})")

    manifest_path = OUT_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "renderColor": RENDER_COLOR,
                "renderSize": ICON_SIZE,
                "icons": manifest,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"wrote {written} icons to {OUT_DIR.relative_to(ROOT)}")
    if skipped:
        print(f"skipped {len(skipped)}:", file=sys.stderr)
        for entry in skipped:
            print(f"  - {entry}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
