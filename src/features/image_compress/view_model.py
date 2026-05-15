from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from app.concurrency import PythonTaskRunner

from .service import ImageCompressService


class ImageCompressViewModel(QObject):
    imageCompressed = Signal(str)
    filesChanged = Signal("QVariantList")
    _uiCallback = Signal(object)

    def __init__(self, initial_files: list[str] | None = None) -> None:
        super().__init__()
        self._disposed = False
        self._service = ImageCompressService()
        self._runner = PythonTaskRunner(thread_name_prefix="image-compress")
        self._uiCallback.connect(self._run_ui_callback)
        self._initial_files = list(initial_files or [])

    @Slot(result="QVariantList")
    def initialFiles(self) -> list[str]:
        return list(self._initial_files)

    @Slot("QVariantList")
    def setFiles(self, files) -> None:
        next_files = [str(item) for item in files if str(item)]
        if next_files == self._initial_files:
            return
        self._initial_files = next_files
        self.filesChanged.emit(list(self._initial_files))

    @Slot("QVariantList", int, str)
    def compressImages(self, fileUrls, quality: int, mode: str) -> None:
        files = list(fileUrls or [])
        self._runner.start(
            lambda: self._service.compress_images(files, quality, mode),
            on_success=lambda message: self._emit_compressed(str(message or "")),
            on_error=lambda exc: self._emit_compressed(f"压缩失败: {exc}"),
        )

    def dispose(self) -> None:
        self._disposed = True
        self._runner.shutdown(wait=False)

    def _emit_compressed(self, message: str) -> None:
        self._post_ui(lambda value=message: self._emit_compressed_in_ui(value))

    def _post_ui(self, fn) -> None:
        self._uiCallback.emit(fn)

    @Slot(object)
    def _run_ui_callback(self, fn: object) -> None:
        if not self._disposed and callable(fn):
            fn()

    def _emit_compressed_in_ui(self, message: str) -> None:
        if not self._disposed:
            self.imageCompressed.emit(message)
