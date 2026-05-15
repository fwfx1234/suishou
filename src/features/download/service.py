from __future__ import annotations

import time
from pathlib import Path
from threading import Lock
from typing import Callable

import requests

from app.concurrency import PythonTaskRunner, TaskHandle
from app.logging import get_logger, make_task_id


class DownloadService:
    def __init__(
        self,
        on_tasks_updated: Callable[[list[dict]], None],
        on_download_finished: Callable[[str], None],
    ) -> None:
        self._on_tasks_updated = on_tasks_updated
        self._on_download_finished = on_download_finished
        self._tasks: list[dict] = []
        self._cancelled: set[str] = set()
        self._lock = Lock()
        self._runner = PythonTaskRunner(thread_name_prefix="download-task")
        self._task_handles: dict[str, TaskHandle] = {}
        self._log = get_logger("features.download.service", plugin_id="download")

    def download_file(self, url: str, save_path: str) -> None:
        task_id = make_task_id()
        task = {
            "id": task_id,
            "url": url,
            "savePath": save_path,
            "status": "下载中",
            "progress": 0,
            "speed": "0 KB/s",
        }
        with self._lock:
            self._tasks.append(task)
        self._log.info("download.start", "开始下载", taskId=task_id, urlLength=len(url or ""), targetName=Path(save_path).name)
        self._emit_tasks()
        handle = self._runner.start(
            lambda task_handle: self._download_worker(task_handle, task_id, url, save_path),
            on_success=lambda message: self._on_download_finished(str(message or "")),
            on_error=lambda exc: self._handle_download_error(task_id, exc),
            on_done=lambda: self._remove_task_handle(task_id),
        )
        should_cancel = False
        with self._lock:
            if task_id in self._cancelled:
                should_cancel = True
            elif handle._future is None or not handle._future.done():
                self._task_handles[task_id] = handle
        if should_cancel:
            handle.cancel()

    def clear_tasks(self) -> None:
        with self._lock:
            self._tasks = []
        self._emit_tasks()

    def cancel_task(self, task_id: str) -> None:
        clean_id = str(task_id or "")
        if not clean_id:
            return
        with self._lock:
            self._cancelled.add(clean_id)
            handle = self._task_handles.get(clean_id)
        if handle is not None:
            handle.cancel()
        self._log.info("download.cancel_requested", "请求取消下载", taskId=clean_id)
        self._update_task(clean_id, {"status": "正在取消", "speed": "0 KB/s"})

    def close(self) -> None:
        with self._lock:
            self._cancelled.update(str(task.get("id") or "") for task in self._tasks)
            self._task_handles.clear()
        self._runner.shutdown(wait=False)

    def _download_worker(self, handle: TaskHandle, task_id: str, url: str, save_path: str) -> str:
        target = Path(save_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        try:
            with requests.get(url, stream=True, timeout=30) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", "0") or "0")
                start_at = time.time()
                with target.open("wb") as file_obj:
                    for chunk in resp.iter_content(chunk_size=1024 * 64):
                        if self._is_cancelled(task_id) or handle.cancelled:
                            self._remove_partial(target)
                            self._update_task(task_id, {"status": "已取消", "progress": 0, "speed": "0 KB/s"})
                            self._log.info("download.cancelled", "下载已取消", taskId=task_id, targetName=target.name)
                            return f"已取消: {target.name}"
                        if not chunk:
                            continue
                        file_obj.write(chunk)
                        written += len(chunk)
                        elapsed = max(time.time() - start_at, 0.1)
                        speed_kb = written / 1024 / elapsed
                        progress = int((written * 100) / total) if total > 0 else 0
                        self._update_task(
                            task_id,
                            {
                                "status": "下载中",
                                "progress": progress,
                                "speed": f"{speed_kb:.1f} KB/s",
                            },
                        )
        finally:
            with self._lock:
                self._cancelled.discard(task_id)
        size_text = f"{written/1024:.1f}KB"
        if "total" in locals() and total > 0:
            size_text = f"{written/1024:.1f}KB / {total/1024:.1f}KB"
        self._update_task(task_id, {"status": "下载完成", "progress": 100, "speed": "0 KB/s"})
        self._log.info("download.complete", "下载完成", taskId=task_id, targetName=target.name, bytes=written)
        return f"下载完成: {target.name} ({size_text})"

    def _handle_download_error(self, task_id: str, exc: BaseException) -> None:
        self._update_task(task_id, {"status": f"下载失败: {exc}", "speed": "0 KB/s"})
        self._log.warning("download.failed", "下载失败", taskId=task_id, error=str(exc))
        self._on_download_finished(f"下载失败: {exc}")

    def _update_task(self, task_id: str, data: dict) -> None:
        self._update_task_state(task_id, data)

    def _update_task_state(self, task_id: str, data: dict) -> None:
        with self._lock:
            for task in self._tasks:
                if task.get("id") == task_id:
                    task.update(data)
                    break
        self._emit_tasks()

    def _emit_tasks(self) -> None:
        with self._lock:
            items = [dict(task) for task in self._tasks]
        self._on_tasks_updated(items)

    def _is_cancelled(self, task_id: str) -> bool:
        with self._lock:
            return task_id in self._cancelled

    def _remove_task_handle(self, task_id: str) -> None:
        with self._lock:
            self._task_handles.pop(task_id, None)

    @staticmethod
    def _remove_partial(target: Path) -> None:
        try:
            if target.exists():
                target.unlink()
        except OSError:
            pass
