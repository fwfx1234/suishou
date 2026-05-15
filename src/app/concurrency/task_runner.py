from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from inspect import signature
from threading import Event, Lock
from uuid import uuid4


TaskFunction = Callable[[], object] | Callable[["TaskHandle"], object]
TaskCallback = Callable[[object], None]
TaskErrorCallback = Callable[[BaseException], None]
TaskDoneCallback = Callable[[], None]


@dataclass(slots=True)
class TaskHandle:
    id: str
    cancel_event: Event = field(default_factory=Event)
    _future: Future | None = None

    def cancel(self) -> None:
        self.cancel_event.set()
        if self._future is not None:
            self._future.cancel()

    @property
    def cancelled(self) -> bool:
        return self.cancel_event.is_set()


class PythonTaskRunner:
    def __init__(self, *, max_workers: int | None = None, thread_name_prefix: str = "app-task") -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix=thread_name_prefix)
        self._callbacks: dict[str, tuple[TaskCallback | None, TaskErrorCallback | None, TaskDoneCallback | None]] = {}
        self._handles: dict[str, TaskHandle] = {}
        self._lock = Lock()
        self._shutdown = False

    def start(
        self,
        fn: TaskFunction,
        *,
        on_success: TaskCallback | None = None,
        on_error: TaskErrorCallback | None = None,
        on_done: TaskDoneCallback | None = None,
    ) -> TaskHandle:
        with self._lock:
            if self._shutdown:
                raise RuntimeError("Task runner has been shut down")
            task_id = uuid4().hex
            handle = TaskHandle(task_id)
            self._callbacks[task_id] = (on_success, on_error, on_done)
            self._handles[task_id] = handle
            try:
                future = self._executor.submit(self._run_task, fn, handle)
            except BaseException:
                self._callbacks.pop(task_id, None)
                self._handles.pop(task_id, None)
                raise
            handle._future = future
        future.add_done_callback(lambda done, tid=task_id: self._handle_done(tid, done))
        return handle

    def cancel(self, task_id: str) -> None:
        with self._lock:
            handle = self._handles.pop(task_id, None)
            self._callbacks.pop(task_id, None)
        if handle is not None:
            handle.cancel()

    def cancel_all(self) -> None:
        with self._lock:
            handles = list(self._handles.values())
            self._handles.clear()
            self._callbacks.clear()
        for handle in handles:
            handle.cancel()

    def shutdown(self, *, wait: bool = False) -> None:
        with self._lock:
            if self._shutdown:
                return
            self._shutdown = True
            handles = list(self._handles.values())
            self._handles.clear()
            self._callbacks.clear()
        for handle in handles:
            handle.cancel()
        self._executor.shutdown(wait=wait, cancel_futures=True)

    @staticmethod
    def _run_task(fn: TaskFunction, handle: TaskHandle) -> object:
        params = signature(fn).parameters
        if not params:
            return fn()  # type: ignore[misc]
        return fn(handle)  # type: ignore[misc]

    def _handle_done(self, task_id: str, future: Future) -> None:
        with self._lock:
            callbacks = self._callbacks.pop(task_id, None)
            handle = self._handles.pop(task_id, None)
        if callbacks is None:
            return
        on_success, on_error, on_done = callbacks
        try:
            if handle is not None and handle.cancelled:
                return
            try:
                result = future.result()
            except BaseException as exc:
                if on_error is not None:
                    on_error(exc)
                return
            if on_success is not None:
                on_success(result)
        finally:
            if on_done is not None:
                on_done()
