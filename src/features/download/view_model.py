from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from .service import DownloadService


class DownloadViewModel(QObject):
    downloadFinished = Signal(str)
    downloadTaskUpdated = Signal("QVariantList")
    _uiCallback = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._disposed = False
        self._uiCallback.connect(self._run_ui_callback)
        self._service = DownloadService(
            on_tasks_updated=self._emit_tasks_updated,
            on_download_finished=self._emit_download_finished,
        )

    @Slot(str, str)
    def downloadFile(self, url: str, savePath: str) -> None:
        self._service.download_file(url, savePath)

    @Slot()
    def clearDownloadTasks(self) -> None:
        self._service.clear_tasks()

    @Slot(str)
    def cancelDownloadTask(self, taskId: str) -> None:
        self._service.cancel_task(taskId)

    def dispose(self) -> None:
        self._disposed = True
        self._service.close()

    def _emit_tasks_updated(self, items: list[dict]) -> None:
        self._post_ui(lambda payload=list(items): self._emit_tasks_updated_in_ui(payload))

    def _emit_download_finished(self, message: str) -> None:
        self._post_ui(lambda value=str(message): self._emit_download_finished_in_ui(value))

    def _post_ui(self, fn) -> None:
        self._uiCallback.emit(fn)

    @Slot(object)
    def _run_ui_callback(self, fn: object) -> None:
        if not self._disposed and callable(fn):
            fn()

    def _emit_tasks_updated_in_ui(self, items: list[dict]) -> None:
        if not self._disposed:
            self.downloadTaskUpdated.emit(items)

    def _emit_download_finished_in_ui(self, message: str) -> None:
        if not self._disposed:
            self.downloadFinished.emit(message)
