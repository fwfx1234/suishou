from __future__ import annotations

import ctypes
import struct
import time
from contextlib import contextmanager
from ctypes import wintypes
from io import BytesIO
from pathlib import Path
from threading import Event, Thread

from app.services.clipboard.models import ClipboardItemDraft

CF_DIB = 8
CF_HDROP = 15
CF_UNICODETEXT = 13
GHND = 0x0042

GMEM_MOVEABLE = 0x0002

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32

# Configure ctypes signatures so 64-bit pointer returns are not truncated to int.
user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wintypes.BOOL
user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32.SetClipboardData.restype = wintypes.HANDLE
user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = wintypes.BOOL
user32.GetClipboardSequenceNumber.argtypes = []
user32.GetClipboardSequenceNumber.restype = wintypes.DWORD

kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalLock.restype = wintypes.LPVOID
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = wintypes.BOOL
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalFree.restype = wintypes.HGLOBAL
kernel32.GlobalSize.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalSize.restype = ctypes.c_size_t

shell32.DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
shell32.DragQueryFileW.restype = wintypes.UINT


class DROPFILES(ctypes.Structure):
    _fields_ = [
        ("pFiles", wintypes.DWORD),
        ("x", wintypes.LONG),
        ("y", wintypes.LONG),
        ("fNC", wintypes.BOOL),
        ("fWide", wintypes.BOOL),
    ]


class Win32ClipboardBackend:
    def __init__(self, *, poll_interval: float = 0.2) -> None:
        self._poll_interval = max(0.05, float(poll_interval))
        self._callback = None
        self._thread: Thread | None = None
        self._stop_event = Event()
        self._last_sequence = 0
        self._last_signature = ""
        self._suppress_signature = ""

    def start(self, on_change) -> None:
        self._callback = on_change
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._last_sequence = int(user32.GetClipboardSequenceNumber())
        self._thread = Thread(
            target=self._poll_loop,
            name="clipboard-win32-listener",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._thread = None
        self._callback = None

    def read_current(self) -> ClipboardItemDraft | None:
        try:
            with _open_clipboard():
                if user32.IsClipboardFormatAvailable(CF_HDROP):
                    paths = _read_file_paths()
                    if paths:
                        names = [Path(path).name or path for path in paths]
                        preview = ", ".join(names[:3])
                        if len(names) > 3:
                            preview += f" ... (+{len(names) - 3})"
                        return ClipboardItemDraft(
                            item_type="files",
                            preview=preview,
                            metadata={"count": len(paths), "paths": paths},
                        )
                if user32.IsClipboardFormatAvailable(CF_DIB):
                    image = _read_image_draft()
                    if image is not None:
                        return image
                if user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
                    text = _read_text()
                    if text:
                        return ClipboardItemDraft(
                            item_type="text",
                            content=text,
                            preview=_compact_preview(text),
                        )
        except Exception:
            return None
        return None

    def read_text(self) -> str:
        draft = self.read_current()
        if draft is None or draft.item_type != "text":
            return ""
        return draft.content

    def write_text(self, text: str) -> None:
        encoded = text.encode("utf-16le") + b"\x00\x00"
        handle = self._alloc_bytes(encoded)
        try:
            with _open_clipboard():
                if not user32.EmptyClipboard():
                    raise OSError("无法清空剪贴板")
                if not user32.SetClipboardData(CF_UNICODETEXT, handle):
                    raise OSError("写入文本失败")
                handle = None
            self._suppress_signature = f"text:{text}"
            self._last_signature = self._suppress_signature
        finally:
            if handle:
                kernel32.GlobalFree(handle)

    def write_files(self, paths: list[str]) -> None:
        clean_paths = [str(Path(path)) for path in paths if path]
        if not clean_paths:
            raise ValueError("文件列表为空")
        for path in clean_paths:
            if not Path(path).exists():
                raise FileNotFoundError(path)
        payload = ("\0".join(clean_paths) + "\0\0").encode("utf-16le")
        dropfiles = DROPFILES()
        dropfiles.pFiles = ctypes.sizeof(DROPFILES)
        dropfiles.fWide = True
        size = ctypes.sizeof(DROPFILES) + len(payload)
        handle = kernel32.GlobalAlloc(GHND, size)
        if not handle:
            raise MemoryError("分配剪贴板内存失败")
        locked = kernel32.GlobalLock(handle)
        if not locked:
            kernel32.GlobalFree(handle)
            raise MemoryError("锁定剪贴板内存失败")
        try:
            ctypes.memmove(locked, ctypes.byref(dropfiles), ctypes.sizeof(DROPFILES))
            ctypes.memmove(locked + ctypes.sizeof(DROPFILES), payload, len(payload))
        finally:
            kernel32.GlobalUnlock(handle)
        try:
            with _open_clipboard():
                if not user32.EmptyClipboard():
                    raise OSError("无法清空剪贴板")
                if not user32.SetClipboardData(CF_HDROP, handle):
                    raise OSError("写入文件失败")
                handle = None
            self._suppress_signature = "files:" + "|".join(clean_paths)
            self._last_signature = self._suppress_signature
        finally:
            if handle:
                kernel32.GlobalFree(handle)

    def write_image(self, path: str | Path) -> None:
        from PIL import Image

        image_path = Path(path)
        if not image_path.exists():
            raise FileNotFoundError(str(image_path))
        with Image.open(image_path) as image:
            normalized = image.convert("RGBA")
            png_bytes = _image_to_png_bytes(normalized)
            bmp_buffer = BytesIO()
            normalized.save(bmp_buffer, format="BMP")
            dib_bytes = bmp_buffer.getvalue()[14:]
        handle = self._alloc_bytes(dib_bytes)
        try:
            with _open_clipboard():
                if not user32.EmptyClipboard():
                    raise OSError("无法清空剪贴板")
                if not user32.SetClipboardData(CF_DIB, handle):
                    raise OSError("写入图片失败")
                handle = None
            self._suppress_signature = f"image:{len(png_bytes)}:{hash(png_bytes)}"
            self._last_signature = self._suppress_signature
        finally:
            if handle:
                kernel32.GlobalFree(handle)

    def clear(self) -> None:
        with _open_clipboard():
            if not user32.EmptyClipboard():
                raise OSError("无法清空剪贴板")
        self._suppress_signature = ""
        self._last_signature = ""

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            sequence = int(user32.GetClipboardSequenceNumber())
            if sequence and sequence != self._last_sequence:
                self._last_sequence = sequence
                draft = self.read_current()
                signature = _draft_signature(draft)
                if draft is not None and signature and signature != self._last_signature:
                    if signature == self._suppress_signature:
                        self._suppress_signature = ""
                        self._last_signature = signature
                    elif callable(self._callback):
                        self._last_signature = signature
                        self._callback(draft)
            self._stop_event.wait(self._poll_interval)

    @staticmethod
    def _alloc_bytes(data: bytes):
        handle = kernel32.GlobalAlloc(GHND, len(data))
        if not handle:
            raise MemoryError("分配剪贴板内存失败")
        locked = kernel32.GlobalLock(handle)
        if not locked:
            kernel32.GlobalFree(handle)
            raise MemoryError("锁定剪贴板内存失败")
        try:
            ctypes.memmove(locked, data, len(data))
        finally:
            kernel32.GlobalUnlock(handle)
        return handle


@contextmanager
def _open_clipboard(retries: int = 15, delay: float = 0.02):
    for index in range(retries):
        if user32.OpenClipboard(None):
            try:
                yield
            finally:
                user32.CloseClipboard()
            return
        if index < retries - 1:
            time.sleep(delay)
    raise OSError("无法打开剪贴板")


def _read_text() -> str:
    handle = user32.GetClipboardData(CF_UNICODETEXT)
    if not handle:
        return ""
    locked = kernel32.GlobalLock(handle)
    if not locked:
        return ""
    try:
        return ctypes.wstring_at(locked).rstrip("\x00")
    finally:
        kernel32.GlobalUnlock(handle)


def _read_file_paths() -> list[str]:
    handle = user32.GetClipboardData(CF_HDROP)
    if not handle:
        return []
    count = shell32.DragQueryFileW(handle, 0xFFFFFFFF, None, 0)
    paths: list[str] = []
    for index in range(int(count)):
        length = shell32.DragQueryFileW(handle, index, None, 0)
        if length <= 0:
            continue
        buffer = ctypes.create_unicode_buffer(length + 1)
        shell32.DragQueryFileW(handle, index, buffer, length + 1)
        if buffer.value:
            paths.append(buffer.value)
    return paths


def _read_image_draft() -> ClipboardItemDraft | None:
    handle = user32.GetClipboardData(CF_DIB)
    if not handle:
        return None
    size = kernel32.GlobalSize(handle)
    if size <= 0:
        return None
    locked = kernel32.GlobalLock(handle)
    if not locked:
        return None
    try:
        raw = ctypes.string_at(locked, size)
    finally:
        kernel32.GlobalUnlock(handle)
    converted = _dib_to_png(raw)
    if converted is None:
        return None
    png_bytes, width, height = converted
    return ClipboardItemDraft(
        item_type="image",
        preview=f"{width} x {height} PNG",
        metadata={"width": width, "height": height},
        image_bytes=png_bytes,
    )


def _dib_to_png(raw: bytes) -> tuple[bytes, int, int] | None:
    try:
        from PIL import Image
    except Exception:
        return None
    if len(raw) < 40:
        return None
    header_size = struct.unpack_from("<I", raw, 0)[0]
    width = abs(struct.unpack_from("<i", raw, 4)[0])
    height = abs(struct.unpack_from("<i", raw, 8)[0])
    bit_count = struct.unpack_from("<H", raw, 14)[0]
    compression = struct.unpack_from("<I", raw, 16)[0]
    colors_used = struct.unpack_from("<I", raw, 32)[0] if len(raw) >= 36 else 0
    palette_size = 0
    if bit_count <= 8:
        palette_entries = colors_used or (1 << bit_count)
        palette_size = palette_entries * 4
    elif compression == 3 and bit_count in {16, 32} and header_size == 40:
        palette_size = 12
    offset = 14 + header_size + palette_size
    file_size = 14 + len(raw)
    bmp = b"BM" + struct.pack("<IHHI", file_size, 0, 0, offset) + raw
    try:
        with Image.open(BytesIO(bmp)) as image:
            png = _image_to_png_bytes(image)
            return png, width, height
    except Exception:
        return None


def _image_to_png_bytes(image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _compact_preview(text: str, limit: int = 160) -> str:
    preview = " ".join(text.replace("\r", " ").replace("\n", " ").split())
    if len(preview) > limit:
        return preview[: limit - 3] + "..."
    return preview


def _draft_signature(draft: ClipboardItemDraft | None) -> str:
    if draft is None:
        return ""
    if draft.item_type == "files":
        paths = draft.metadata.get("paths", [])
        if isinstance(paths, list):
            return "files:" + "|".join(str(path) for path in paths)
    if draft.item_type == "image":
        return f"image:{len(draft.image_bytes or b'')}:{hash(draft.image_bytes or b'')}"
    return f"text:{draft.content}"
