from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from .service import PacketCaptureService


class PacketCaptureViewModel(QObject):
    packetRowsUpdated = Signal("QVariantList")

    def __init__(self) -> None:
        super().__init__()
        self._service = PacketCaptureService()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._append_mock_packet)

    @Slot()
    def startPacketCapture(self) -> None:
        self._service.start()
        self._timer.start(1200)

    @Slot()
    def stopPacketCapture(self) -> None:
        self._service.stop()
        self._timer.stop()

    @Slot()
    def clearPacketRows(self) -> None:
        self.packetRowsUpdated.emit(self._service.clear_rows())

    def _append_mock_packet(self) -> None:
        self.packetRowsUpdated.emit(self._service.append_mock_packet())
