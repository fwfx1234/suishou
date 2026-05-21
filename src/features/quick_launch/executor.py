from __future__ import annotations

import os
import shlex
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import RLock
from time import perf_counter
from typing import Callable

from .parameters import MissingParameterError, extract_parameters, substitute, substitute_mapping
from .repository import QuickLaunchAction, QuickLaunchRepository, QuickLaunchRun


@dataclass(slots=True)
class ExecutionResult:
    ok: bool
    status: str  # success | failed | timeout | error | stopped
    message: str = ""
    run: QuickLaunchRun | None = None
    missing_parameters: list[str] | None = None
    feedback_mode: str = "silent"


SCRIPT_INTERPRETERS: dict[str, list[str]] = {
    "shell": ["/bin/zsh"],
    "node": ["node"],
    "python": ["python3"],
}

INLINE_FLAGS: dict[str, str] = {
    "shell": "-c",
    "node": "-e",
    "python": "-c",
}


class QuickLaunchExecutor:
    """Dispatch actions (script / open_path / open_url) and record results."""

    def __init__(
        self,
        repository: QuickLaunchRepository,
        platform: object,
        *,
        subprocess_run=None,
        notification_runner=None,
        thread_pool: ThreadPoolExecutor | None = None,
    ) -> None:
        self._repository = repository
        self._platform = platform
        self._subprocess_run = subprocess_run or self._default_subprocess_run
        if notification_runner is None:
            notifications = getattr(platform, "notifications", None)
            notify = getattr(notifications, "notify", None) if notifications is not None else None
            notification_runner = notify or self._noop_notification_runner
        self._notification_runner = notification_runner
        self._thread_pool = thread_pool or ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="quick-launch"
        )
        self._owns_thread_pool = thread_pool is None
        self._running_lock = RLock()
        self._running_ids: set[int] = set()
        self._running_processes: dict[int, subprocess.Popen] = {}
        self._stopping_ids: set[int] = set()
        self._pending_cancel: set[int] = set()

    def is_running(self, action_id: int) -> bool:
        with self._running_lock:
            return int(action_id) in self._running_ids

    def stop(self, action_id: int) -> bool:
        """Best-effort terminate of a running action's process."""
        key = int(action_id)
        with self._running_lock:
            proc = self._running_processes.get(key)
            if proc is None:
                # Task is queued but Popen hasn't registered yet — mark for cancel
                # so the worker bails as soon as the proc starts.
                if key in self._running_ids:
                    self._pending_cancel.add(key)
                    self._stopping_ids.add(key)
                    return True
                return False
            self._stopping_ids.add(key)
        try:
            proc.terminate()
            return True
        except Exception:
            with self._running_lock:
                self._stopping_ids.discard(key)
            return False

    def stop_all(self) -> None:
        with self._running_lock:
            items = list(self._running_processes.items())
            for action_id, _ in items:
                self._stopping_ids.add(action_id)
        for _, proc in items:
            try:
                proc.terminate()
            except Exception:
                pass

    def execute_in_background(
        self,
        action: QuickLaunchAction,
        *,
        parameters: dict[str, str] | None = None,
        on_done: Callable[[ExecutionResult], None] | None = None,
    ) -> bool:
        """Run an action off the main thread. Returns False if already running."""
        with self._running_lock:
            if action.id in self._running_ids:
                return False
            self._running_ids.add(action.id)
            self._pending_cancel.discard(action.id)
            self._stopping_ids.discard(action.id)

        def _task() -> None:
            try:
                result = self.execute(action, parameters=parameters)
            finally:
                with self._running_lock:
                    self._running_ids.discard(action.id)
            if on_done is not None:
                try:
                    on_done(result)
                except Exception:
                    pass

        self._thread_pool.submit(_task)
        return True

    def shutdown(self, wait: bool = False) -> None:
        self.stop_all()
        if self._owns_thread_pool:
            self._thread_pool.shutdown(wait=wait, cancel_futures=True)

    def required_parameters(self, action: QuickLaunchAction) -> list[str]:
        sources = [
            action.path,
            action.url,
            action.args,
            action.cwd,
            action.interpreter,
            action.script_body,
        ]
        sources.extend(action.env.values())
        return [spec.name for spec in extract_parameters(*sources)]

    def execute(
        self,
        action: QuickLaunchAction,
        *,
        parameters: dict[str, str] | None = None,
    ) -> ExecutionResult:
        values = {str(k): "" if v is None else str(v) for k, v in (parameters or {}).items()}
        try:
            if action.kind == "script":
                result = self._execute_script(action, values)
            elif action.kind == "open_path":
                result = self._execute_open_path(action, values)
            elif action.kind == "open_url":
                result = self._execute_open_url(action, values)
            else:
                result = self._record_error(action, f"未知动作类型: {action.kind}")
        except MissingParameterError as exc:
            return ExecutionResult(
                ok=False,
                status="error",
                message=str(exc),
                missing_parameters=list(exc.missing),
                feedback_mode=action.feedback_mode,
            )
        result.feedback_mode = action.feedback_mode
        if action.feedback_mode == "notification":
            self._emit_notification(action, result)
        return result

    # ----- kind handlers -----

    def _execute_script(self, action: QuickLaunchAction, values: dict[str, str]) -> ExecutionResult:
        if action.script_source == "inline":
            body = substitute(action.script_body, values, quote=False)
            if not body.strip():
                return self._record_error(action, "脚本内容为空")
            argv = self._build_inline_argv(action, body, values)
        else:
            path = substitute(action.path, values, quote=False).strip()
            if not path:
                return self._record_error(action, "脚本路径为空")
            argv = self._build_script_argv(action, path, values)
        cwd = self._resolve_cwd(action, values)
        env = self._resolve_env(action, values)
        return self._dispatch_capture(action, argv, cwd=cwd, env=env)

    def _execute_open_path(
        self, action: QuickLaunchAction, values: dict[str, str]
    ) -> ExecutionResult:
        path = substitute(action.path, values, quote=False).strip()
        if not path:
            return self._record_error(action, "目标路径为空")
        result = self._platform.open_path(path)
        return self._record_platform_result(action, result, "open_path")

    def _execute_open_url(
        self, action: QuickLaunchAction, values: dict[str, str]
    ) -> ExecutionResult:
        url = substitute(action.url, values, quote=False).strip()
        if not url:
            return self._record_error(action, "URL 为空")
        result = self._platform.open_url(url)
        return self._record_platform_result(action, result, "open_url")

    # ----- script argv construction -----

    def _build_script_argv(
        self,
        action: QuickLaunchAction,
        path: str,
        values: dict[str, str],
    ) -> list[str]:
        interpreter_argv = self._interpreter_argv(action, values)
        extra_args_str = substitute(action.args, values, quote=False).strip()
        extra_args = shlex.split(extra_args_str) if extra_args_str else []
        return [*interpreter_argv, path, *extra_args]

    def _build_inline_argv(
        self,
        action: QuickLaunchAction,
        body: str,
        values: dict[str, str],
    ) -> list[str]:
        extra_args_str = substitute(action.args, values, quote=False).strip()
        extra_args = shlex.split(extra_args_str) if extra_args_str else []
        override = substitute(action.interpreter, values, quote=False).strip()
        if override:
            interpreter_argv = shlex.split(override)
            return [*interpreter_argv, body, *extra_args]
        flag = INLINE_FLAGS.get(action.script_type, "-c")
        interpreter_argv = list(SCRIPT_INTERPRETERS.get(action.script_type, ["/bin/zsh"]))
        argv = [*interpreter_argv, flag, body]
        if action.script_type == "shell":
            argv.append("quick-launch")
        return [*argv, *extra_args]

    def _interpreter_argv(
        self, action: QuickLaunchAction, values: dict[str, str]
    ) -> list[str]:
        override = substitute(action.interpreter, values, quote=False).strip()
        if override:
            return shlex.split(override)
        if action.script_type in SCRIPT_INTERPRETERS:
            return list(SCRIPT_INTERPRETERS[action.script_type])
        # "other" without explicit interpreter → execute directly via shell
        return ["/bin/zsh"]

    # ----- dispatch -----

    def _dispatch_capture(
        self,
        action: QuickLaunchAction,
        argv: list[str],
        *,
        cwd: str | None,
        env: dict[str, str] | None,
    ) -> ExecutionResult:
        started_at = self._now()
        start_ts = perf_counter()
        timeout = action.timeout_sec if action.timeout_sec and action.timeout_sec > 0 else None
        capture = action.feedback_mode != "silent"

        def _on_started(proc: subprocess.Popen) -> None:
            with self._running_lock:
                self._running_processes[action.id] = proc
                should_kill = action.id in self._pending_cancel
                self._pending_cancel.discard(action.id)
            if should_kill:
                try:
                    proc.terminate()
                except Exception:
                    pass

        try:
            try:
                completed = self._subprocess_run(
                    argv,
                    cwd=cwd or None,
                    env=env,
                    timeout=timeout,
                    capture=capture,
                    on_started=_on_started,
                )
            except subprocess.TimeoutExpired as exc:
                duration_ms = int((perf_counter() - start_ts) * 1000)
                finished_at = self._now()
                run = self._repository.record_run(
                    action_id=action.id,
                    status="timeout",
                    exit_code=None,
                    stdout=self._coerce_stream(exc.stdout) if capture else "",
                    stderr=self._coerce_stream(exc.stderr) if capture else "",
                    duration_ms=duration_ms,
                    started_at=started_at,
                    finished_at=finished_at,
                    message=f"执行超时 ({action.timeout_sec}s)",
                )
                return ExecutionResult(ok=False, status="timeout", message=run.message, run=run)
            except FileNotFoundError as exc:
                return self._record_error(action, f"找不到可执行文件: {exc}")
            except OSError as exc:
                return self._record_error(action, f"执行失败: {exc}")
        finally:
            with self._running_lock:
                self._running_processes.pop(action.id, None)
                was_stopped = action.id in self._stopping_ids
                self._stopping_ids.discard(action.id)

        duration_ms = int((perf_counter() - start_ts) * 1000)
        finished_at = self._now()
        exit_code = int(completed.returncode)
        if was_stopped:
            status = "stopped"
            message = "已手动停止"
        elif exit_code == 0:
            status = "success"
            message = ""
        else:
            status = "failed"
            message = f"退出码 {exit_code}"
        stdout = self._coerce_stream(getattr(completed, "stdout", "")) if capture else ""
        stderr = self._coerce_stream(getattr(completed, "stderr", "")) if capture else ""
        run = self._repository.record_run(
            action_id=action.id,
            status=status,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            started_at=started_at,
            finished_at=finished_at,
            message=message,
        )
        return ExecutionResult(ok=status == "success", status=status, message=run.message, run=run)

    # ----- helpers -----

    def _resolve_cwd(self, action: QuickLaunchAction, values: dict[str, str]) -> str | None:
        cwd = substitute(action.cwd, values, quote=False).strip()
        return cwd or None

    def _resolve_env(
        self, action: QuickLaunchAction, values: dict[str, str]
    ) -> dict[str, str] | None:
        if not action.env:
            return None
        merged = os.environ.copy()
        substituted = substitute_mapping(action.env, values, quote=False)
        merged.update({str(k): str(v) for k, v in substituted.items()})
        return merged

    @staticmethod
    def _coerce_stream(data: object) -> str:
        if data is None:
            return ""
        if isinstance(data, bytes):
            return data.decode("utf-8", errors="replace")
        return str(data)

    @staticmethod
    def _now() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _record_error(self, action: QuickLaunchAction, message: str) -> ExecutionResult:
        now = self._now()
        run = self._repository.record_run(
            action_id=action.id,
            status="error",
            exit_code=None,
            stdout="",
            stderr=message,
            duration_ms=0,
            started_at=now,
            finished_at=now,
            message=message,
        )
        return ExecutionResult(ok=False, status="error", message=message, run=run)

    def _record_platform_result(
        self,
        action: QuickLaunchAction,
        result: object,
        kind: str,
    ) -> ExecutionResult:
        ok = bool(getattr(result, "ok", False))
        message = str(getattr(result, "message", "") or "")
        now = self._now()
        run = self._repository.record_run(
            action_id=action.id,
            status="success" if ok else "error",
            exit_code=None,
            stdout="",
            stderr="" if ok else message,
            duration_ms=0,
            started_at=now,
            finished_at=now,
            message=message or kind,
        )
        return ExecutionResult(ok=ok, status="success" if ok else "error", message=message, run=run)

    def _emit_notification(self, action: QuickLaunchAction, result: ExecutionResult) -> None:
        title = action.name or "快速启动"
        if result.ok:
            body = f"执行成功 · {action.name}"
        else:
            body = result.message or f"执行失败 · {result.status}"
        try:
            self._notification_runner(title=title, body=body, success=result.ok)
        except Exception:
            pass

    @staticmethod
    def _default_subprocess_run(argv, *, cwd, env, timeout, capture, on_started=None):
        popen_kwargs: dict = {"cwd": cwd, "env": env, "start_new_session": True}
        if capture:
            popen_kwargs.update(
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        else:
            popen_kwargs.update(
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        proc = subprocess.Popen(argv, **popen_kwargs)
        if on_started is not None:
            on_started(proc)
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                stdout, stderr = proc.communicate()
            except Exception:
                stdout, stderr = ("", "") if capture else (None, None)
            raise subprocess.TimeoutExpired(argv, timeout, output=stdout, stderr=stderr)
        return subprocess.CompletedProcess(argv, proc.returncode, stdout=stdout, stderr=stderr)

    @staticmethod
    def _noop_notification_runner(*, title: str, body: str, success: bool | None = None) -> None:
        del title, body, success
