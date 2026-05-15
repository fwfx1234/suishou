from __future__ import annotations

import random


class PacketCaptureService:
    def __init__(self) -> None:
        self._capture_running = False
        self._rows: list[dict] = []

    def start(self) -> None:
        self._capture_running = True

    def stop(self) -> None:
        self._capture_running = False

    def clear_rows(self) -> list[dict]:
        self._rows = []
        return self.rows()

    def append_mock_packet(self) -> list[dict]:
        if not self._capture_running:
            return self.rows()
        methods = ["GET", "POST", "PUT", "DELETE"]
        paths = ["/api/users", "/api/login", "/api/order/12", "/api/system/ping", "/v1/files/upload"]
        status_codes = ["200", "201", "400", "401", "404", "500"]
        row = {
            "method": random.choice(methods),
            "path": random.choice(paths),
            "status": random.choice(status_codes),
            "size": f"{random.randint(1, 120)}KB",
        }
        self._rows = [row] + self._rows[:200]
        return self.rows()

    def rows(self) -> list[dict]:
        return [dict(row) for row in self._rows]
