"""生成打包用的 App 图标：紫蓝渐变圆角方 + 居中白色 rocket。

输出：
- assets/app_icon/app_icon.png  （1024 主图）
- assets/app_icon/app_icon.ico  （多分辨率 Windows ICO）
- assets/app_icon/app_icon.icns （macOS，依赖 iconutil/sips）

用法：
    uv run python tools/generate_app_icon.py
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "assets" / "app_icon"

CANVAS_SIZE = 1024
PADDING = 100
CORNER_RADIUS = 224  # macOS Big Sur 风格圆角

GRADIENT_TOP = (139, 92, 246)    # #8B5CF6
GRADIENT_BOTTOM = (59, 130, 246) # #3B82F6


def _ensure_qt_app() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    if QGuiApplication.instance() is None:
        QGuiApplication(sys.argv)


def render_rocket_glyph(size_px: int) -> Image.Image:
    """通过 qtawesome 渲染 fa5s.rocket 为白色 RGBA。"""
    _ensure_qt_app()
    import qtawesome as qta
    from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QSize

    icon = qta.icon("fa5s.rocket", color="white")
    qpixmap = icon.pixmap(QSize(size_px, size_px))
    qimage = qpixmap.toImage()

    buf = QByteArray()
    qbuffer = QBuffer(buf)
    qbuffer.open(QIODevice.WriteOnly)
    qimage.save(qbuffer, "PNG")
    qbuffer.close()

    return Image.open(io.BytesIO(bytes(buf))).convert("RGBA")


def make_gradient(width: int, height: int, top: tuple, bottom: tuple) -> Image.Image:
    base = Image.new("RGB", (width, height))
    pixels = base.load()
    last = max(1, height - 1)
    for y in range(height):
        t = y / last
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        for x in range(width):
            pixels[x, y] = (r, g, b)
    return base


def make_rounded_mask(size: int, padding: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (padding, padding, size - padding, size - padding),
        radius=radius,
        fill=255,
    )
    return mask


def add_top_highlight(canvas: Image.Image) -> Image.Image:
    """顶部加一层柔和的高光，让渐变更有立体感。"""
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rounded_rectangle(
        (PADDING, PADDING, CANVAS_SIZE - PADDING, CANVAS_SIZE - PADDING),
        radius=CORNER_RADIUS,
        fill=(255, 255, 255, 36),
    )

    fade_mask = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(fade_mask).rectangle(
        (0, 0, CANVAS_SIZE, CANVAS_SIZE // 2),
        fill=255,
    )
    fade_mask = fade_mask.filter(ImageFilter.GaussianBlur(120))

    blended = Image.composite(overlay, Image.new("RGBA", canvas.size, (0, 0, 0, 0)), fade_mask)
    return Image.alpha_composite(canvas, blended)


def add_rocket_shadow(canvas: Image.Image, rocket: Image.Image, pos: tuple[int, int]) -> Image.Image:
    """火箭下方加一层柔阴影，使其与背景脱开。"""
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    alpha = rocket.split()[-1].point(lambda v: min(int(v * 0.55), 255))
    shadow_layer = Image.new("RGBA", rocket.size, (0, 0, 0, 0))
    shadow_layer.putalpha(alpha)
    shadow.paste(shadow_layer, (pos[0] + 18, pos[1] + 32), shadow_layer)
    shadow = shadow.filter(ImageFilter.GaussianBlur(28))
    return Image.alpha_composite(canvas, shadow)


def build_icon() -> Image.Image:
    gradient = make_gradient(CANVAS_SIZE, CANVAS_SIZE, GRADIENT_TOP, GRADIENT_BOTTOM)
    mask = make_rounded_mask(CANVAS_SIZE, PADDING, CORNER_RADIUS)

    canvas = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0, 0))
    canvas.paste(gradient, (0, 0), mask)
    canvas = add_top_highlight(canvas)

    glyph_size = int(CANVAS_SIZE * 0.54)
    rocket = render_rocket_glyph(glyph_size)
    x = (CANVAS_SIZE - rocket.width) // 2
    y = (CANVAS_SIZE - rocket.height) // 2 - 8

    canvas = add_rocket_shadow(canvas, rocket, (x, y))
    canvas.paste(rocket, (x, y), rocket)

    return canvas


def write_png(image: Image.Image, path: Path) -> None:
    image.save(path, "PNG")


def write_ico(image: Image.Image, path: Path) -> None:
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    image.save(path, format="ICO", sizes=sizes)


def write_icns(master_png: Path, path: Path) -> bool:
    if sys.platform != "darwin":
        return False
    if shutil.which("iconutil") is None or shutil.which("sips") is None:
        return False
    iconset = path.with_suffix(".iconset")
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir(parents=True)
    layout = [
        (16, "16x16"),
        (32, "16x16@2x"),
        (32, "32x32"),
        (64, "32x32@2x"),
        (128, "128x128"),
        (256, "128x128@2x"),
        (256, "256x256"),
        (512, "256x256@2x"),
        (512, "512x512"),
        (1024, "512x512@2x"),
    ]
    for px, name in layout:
        out = iconset / f"icon_{name}.png"
        subprocess.run(
            ["sips", "-z", str(px), str(px), str(master_png), "--out", str(out)],
            check=True,
            capture_output=True,
        )
    subprocess.run(
        ["iconutil", "-c", "icns", str(iconset), "-o", str(path)],
        check=True,
        capture_output=True,
    )
    shutil.rmtree(iconset)
    return True


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    image = build_icon()
    png_path = OUT_DIR / "app_icon.png"
    ico_path = OUT_DIR / "app_icon.ico"
    icns_path = OUT_DIR / "app_icon.icns"
    write_png(image, png_path)
    write_ico(image, ico_path)
    icns_ok = write_icns(png_path, icns_path)

    print(f"PNG  → {png_path}")
    print(f"ICO  → {ico_path}")
    if icns_ok:
        print(f"ICNS → {icns_path}")
    else:
        print("ICNS skipped (not macOS or sips/iconutil unavailable)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
