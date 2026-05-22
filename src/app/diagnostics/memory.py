"""Lightweight memory diagnostics — no external dependencies.

Snapshots RSS, GC object count, plugin session count, and plugin window count.
Optionally aggregates QObject instance counts by type when explicitly enabled.
"""

from __future__ import annotations

import gc
import os
import subprocess
import sys
import weakref
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QObject, QTimer


def _rss_bytes() -> int:
    """Return resident set size in bytes, or -1 if unavailable."""

    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = _PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(_PROCESS_MEMORY_COUNTERS)
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            ok = ctypes.windll.psapi.GetProcessMemoryInfo(
                handle, ctypes.byref(counters), counters.cb
            )
            if not ok:
                return -1
            return int(counters.WorkingSetSize)
        except Exception:
            return -1

    if sys.platform == "darwin":
        rss = _rss_from_ps()
        if rss > 0:
            return rss
    if sys.platform.startswith("linux"):
        rss = _rss_from_proc_statm()
        if rss > 0:
            return rss

    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except Exception:
        return -1
    # macOS: bytes; Linux: kilobytes
    if sys.platform == "darwin":
        return int(usage)
    return int(usage) * 1024


def _rss_from_ps() -> int:
    try:
        output = subprocess.check_output(
            ["/bin/ps", "-o", "rss=", "-p", str(os.getpid())],
            text=True,
            timeout=1,
        )
        value = int(output.strip().splitlines()[0])
    except Exception:
        return -1
    return value * 1024


def _rss_from_proc_statm() -> int:
    try:
        parts = Path("/proc/self/statm").read_text(encoding="utf-8").split()
        pages = int(parts[1])
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
    except Exception:
        return -1
    return pages * page_size


def _qobject_top(limit: int = 10) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for obj in gc.get_objects():
        try:
            if isinstance(obj, QObject):
                counter[type(obj).__name__] += 1
        except ReferenceError:
            continue
    return counter.most_common(limit)


def snapshot(
    *,
    sessions_count: int = 0,
    windows_count: int = 0,
    include_qobject_top: bool = False,
) -> dict[str, Any]:
    rss = _rss_bytes()
    data: dict[str, Any] = {
        "rssMb": round(rss / (1024 * 1024), 2) if rss > 0 else -1,
        "gcObjects": len(gc.get_objects()),
        "sessions": int(sessions_count),
        "windows": int(windows_count),
    }
    if include_qobject_top:
        data["qobjectTop"] = _qobject_top()
    return data


class MemoryProbe:
    """Hold weak refs to session/surface managers and emit memory snapshots."""

    def __init__(
        self,
        *,
        session_manager: object | None = None,
        surface_coordinator: object | None = None,
        include_qobject_top: bool = False,
    ) -> None:
        self._session_manager_ref = weakref.ref(session_manager) if session_manager is not None else None
        self._surface_coordinator_ref = (
            weakref.ref(surface_coordinator) if surface_coordinator is not None else None
        )
        self._include_qobject_top = include_qobject_top

    def take(self) -> dict[str, Any]:
        return snapshot(
            sessions_count=self._sessions_count(),
            windows_count=self._windows_count(),
            include_qobject_top=self._include_qobject_top,
        )

    def _sessions_count(self) -> int:
        ref = self._session_manager_ref
        if ref is None:
            return 0
        manager = ref()
        if manager is None:
            return 0
        sessions = getattr(manager, "_sessions", None)
        return len(sessions) if sessions is not None else 0

    def _windows_count(self) -> int:
        ref = self._surface_coordinator_ref
        if ref is None:
            return 0
        coordinator = ref()
        if coordinator is None:
            return 0
        windows = getattr(coordinator, "_windows", None)
        return len(windows) if windows is not None else 0


def install_periodic_snapshot(
    qt_app: object,
    probe: MemoryProbe,
    interval_ms: int,
    *,
    log: Callable[..., None],
) -> QTimer | None:
    """Start a recurring memory snapshot timer. Returns None if disabled."""

    if interval_ms <= 0:
        return None
    timer = QTimer(qt_app if isinstance(qt_app, QObject) else None)
    timer.setInterval(int(interval_ms))
    timer.setSingleShot(False)

    def _tick() -> None:
        try:
            log("app.memory.periodic", "周期内存快照", **probe.take())
        except Exception:
            pass

    timer.timeout.connect(_tick)
    timer.start()
    return timer


__all__ = ["MemoryProbe", "install_periodic_snapshot", "snapshot"]
