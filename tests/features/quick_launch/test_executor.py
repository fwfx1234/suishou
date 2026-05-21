from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.storage import SQLiteDatabase

from features.quick_launch.executor import QuickLaunchExecutor
from features.quick_launch.repository import QuickLaunchRepository


@dataclass
class FakeCompleted:
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


class FakePlatformResult:
    def __init__(self, ok: bool, message: str = "") -> None:
        self.ok = ok
        self.message = message


class FakePlatform:
    def __init__(self) -> None:
        self.open_path_calls: list[str] = []
        self.open_url_calls: list[str] = []
        self.path_result = FakePlatformResult(True, "ok")
        self.url_result = FakePlatformResult(True, "ok")

    def open_path(self, path):
        self.open_path_calls.append(str(path))
        return self.path_result

    def open_url(self, url):
        self.open_url_calls.append(str(url))
        return self.url_result


@pytest.fixture
def repository(tmp_path: Path) -> QuickLaunchRepository:
    db = SQLiteDatabase(tmp_path / "ql.db")
    return QuickLaunchRepository(db)


@pytest.fixture
def platform() -> FakePlatform:
    return FakePlatform()


def _make_executor(repo, platform, *, completed=None, notification=None):
    runner = MagicMock(return_value=completed or FakeCompleted())
    notif = notification or MagicMock()
    executor = QuickLaunchExecutor(
        repo, platform,
        subprocess_run=runner,
        notification_runner=notif,
    )
    return executor, runner, notif


def test_required_parameters_extracts_from_path_args_cwd_env(repository, platform) -> None:
    action = repository.create_action(
        name="A",
        kind="script",
        script_type="shell",
        path="${root}/run.sh",
        args="--msg ${msg}",
        cwd="${dir}",
        env={"KEY": "${k}"},
    )
    executor, _, _ = _make_executor(repository, platform)
    assert executor.required_parameters(action) == ["root", "msg", "dir", "k"]


def test_shell_script_uses_zsh_interpreter(repository, platform) -> None:
    action = repository.create_action(
        name="A", kind="script", script_type="shell", path="/tmp/run.sh"
    )
    executor, runner, _ = _make_executor(repository, platform)
    executor.execute(action)
    args = runner.call_args.args[0]
    assert args == ["/bin/zsh", "/tmp/run.sh"]


def test_node_script_uses_node_interpreter(repository, platform) -> None:
    action = repository.create_action(
        name="A", kind="script", script_type="node", path="/tmp/app.js", args="--port 3000"
    )
    executor, runner, _ = _make_executor(repository, platform)
    executor.execute(action)
    args = runner.call_args.args[0]
    assert args == ["node", "/tmp/app.js", "--port", "3000"]


def test_python_script_uses_python3(repository, platform) -> None:
    action = repository.create_action(
        name="A", kind="script", script_type="python", path="/tmp/x.py"
    )
    executor, runner, _ = _make_executor(repository, platform)
    executor.execute(action)
    args = runner.call_args.args[0]
    assert args == ["python3", "/tmp/x.py"]


def test_other_script_with_custom_interpreter(repository, platform) -> None:
    action = repository.create_action(
        name="A", kind="script", script_type="other", interpreter="ruby -W0", path="/tmp/x.rb"
    )
    executor, runner, _ = _make_executor(repository, platform)
    executor.execute(action)
    args = runner.call_args.args[0]
    assert args == ["ruby", "-W0", "/tmp/x.rb"]


def test_inline_shell_script_uses_dash_c(repository, platform) -> None:
    action = repository.create_action(
        name="A", kind="script", script_type="shell",
        script_source="inline", script_body='echo "hi ${name}"', args="alice",
    )
    executor, runner, _ = _make_executor(repository, platform)
    executor.execute(action, parameters={"name": "world"})
    args = runner.call_args.args[0]
    assert args == ["/bin/zsh", "-c", 'echo "hi world"', "quick-launch", "alice"]


def test_inline_python_script_uses_dash_c(repository, platform) -> None:
    action = repository.create_action(
        name="A", kind="script", script_type="python",
        script_source="inline", script_body="print(1)",
    )
    executor, runner, _ = _make_executor(repository, platform)
    executor.execute(action)
    args = runner.call_args.args[0]
    assert args == ["python3", "-c", "print(1)"]


def test_inline_node_script_uses_dash_e(repository, platform) -> None:
    action = repository.create_action(
        name="A", kind="script", script_type="node",
        script_source="inline", script_body="console.log(1)",
    )
    executor, runner, _ = _make_executor(repository, platform)
    executor.execute(action)
    args = runner.call_args.args[0]
    assert args == ["node", "-e", "console.log(1)"]


def test_inline_empty_body_records_error(repository, platform) -> None:
    action = repository.create_action(
        name="A", kind="script", script_type="shell",
        script_source="inline", script_body="   ",
    )
    executor, runner, _ = _make_executor(repository, platform)
    result = executor.execute(action)
    assert result.ok is False and result.status == "error"
    runner.assert_not_called()


def test_inline_required_parameters_extracted_from_body(repository, platform) -> None:
    action = repository.create_action(
        name="A", kind="script", script_type="shell",
        script_source="inline", script_body='echo "${greeting} ${name}"',
    )
    executor, _, _ = _make_executor(repository, platform)
    assert executor.required_parameters(action) == ["greeting", "name"]


def test_execute_in_background_runs_off_calling_thread(repository, platform) -> None:
    import threading
    seen = {}

    def fake_run(argv, *, cwd, env, timeout, capture, on_started=None):
        seen["thread"] = threading.current_thread().name
        return FakeCompleted(returncode=0)

    executor = QuickLaunchExecutor(repository, platform, subprocess_run=fake_run)
    action = repository.create_action(name="A", kind="script", path="/x.sh")
    done = threading.Event()
    executor.execute_in_background(action, on_done=lambda r: done.set())
    assert done.wait(timeout=2.0)
    assert seen["thread"] != threading.current_thread().name


def test_execute_in_background_dedupes_concurrent_calls(repository, platform) -> None:
    import threading
    started = threading.Event()
    release = threading.Event()
    call_count = {"n": 0}

    def fake_run(argv, *, cwd, env, timeout, capture, on_started=None):
        call_count["n"] += 1
        started.set()
        release.wait(timeout=2.0)
        return FakeCompleted(returncode=0)

    executor = QuickLaunchExecutor(repository, platform, subprocess_run=fake_run)
    action = repository.create_action(name="A", kind="script", path="/x.sh")
    finished = threading.Event()
    assert executor.execute_in_background(action, on_done=lambda r: finished.set()) is True
    started.wait(timeout=2.0)
    assert executor.is_running(action.id) is True
    assert executor.execute_in_background(action) is False
    release.set()
    assert finished.wait(timeout=2.0)
    assert call_count["n"] == 1
    assert executor.is_running(action.id) is False


def test_stop_terminates_running_process(repository, platform) -> None:
    import threading
    started = threading.Event()
    release = threading.Event()
    terminated = {"calls": 0}

    class FakeProc:
        def __init__(self) -> None:
            self.returncode = -15

        def terminate(self) -> None:
            terminated["calls"] += 1
            release.set()

    fake_proc = FakeProc()

    def fake_run(argv, *, cwd, env, timeout, capture, on_started=None):
        if on_started is not None:
            on_started(fake_proc)
        started.set()
        release.wait(timeout=2.0)
        return FakeCompleted(returncode=fake_proc.returncode)

    executor = QuickLaunchExecutor(repository, platform, subprocess_run=fake_run)
    action = repository.create_action(name="A", kind="script", path="/x.sh")
    finished = threading.Event()
    executor.execute_in_background(action, on_done=lambda r: finished.set())
    assert started.wait(timeout=2.0)
    assert executor.stop(action.id) is True
    assert finished.wait(timeout=2.0)
    assert terminated["calls"] == 1
    runs = repository.list_runs()
    assert runs[0].status == "stopped"
    assert "已手动停止" in runs[0].message


def test_stop_on_idle_action_returns_false(repository, platform) -> None:
    executor, _, _ = _make_executor(repository, platform)
    action = repository.create_action(name="A", kind="script", path="/x.sh")
    assert executor.stop(action.id) is False


def test_real_subprocess_stop_kills_long_running_inline_script(repository, platform) -> None:
    import threading

    action = repository.create_action(
        name="sleep", kind="script", script_type="shell",
        script_source="inline", script_body="sleep 30", timeout_sec=60,
        feedback_mode="silent",
    )
    executor = QuickLaunchExecutor(repository, platform)
    finished = threading.Event()
    executor.execute_in_background(action, on_done=lambda r: finished.set())
    # Wait for proc to register
    for _ in range(200):
        if executor.is_running(action.id):
            break
        threading.Event().wait(0.01)
    assert executor.is_running(action.id)
    assert executor.stop(action.id) is True
    assert finished.wait(timeout=5.0)
    runs = repository.list_runs()
    assert runs[0].status == "stopped"


def test_stop_all_terminates_each_running_process(repository, platform) -> None:
    import threading

    procs: list = []
    started_events: list = []
    release = threading.Event()

    class FakeProc:
        def __init__(self) -> None:
            self.returncode = 0
            self.terminate_called = False

        def terminate(self) -> None:
            self.terminate_called = True
            self.returncode = -15
            release.set()

    def fake_run(argv, *, cwd, env, timeout, capture, on_started=None):
        proc = FakeProc()
        procs.append(proc)
        if on_started is not None:
            on_started(proc)
        evt = threading.Event()
        started_events.append(evt)
        evt.set()
        release.wait(timeout=2.0)
        return FakeCompleted(returncode=proc.returncode)

    executor = QuickLaunchExecutor(repository, platform, subprocess_run=fake_run)
    a = repository.create_action(name="A", kind="script", path="/a.sh")
    b = repository.create_action(name="B", kind="script", path="/b.sh")
    finished_a = threading.Event()
    finished_b = threading.Event()
    executor.execute_in_background(a, on_done=lambda r: finished_a.set())
    executor.execute_in_background(b, on_done=lambda r: finished_b.set())
    # Wait until both processes have registered
    for _ in range(200):
        if len(procs) == 2:
            break
        threading.Event().wait(0.01)
    assert len(procs) == 2
    executor.stop_all()
    assert finished_a.wait(timeout=2.0)
    assert finished_b.wait(timeout=2.0)
    assert all(p.terminate_called for p in procs)


def test_script_substitutes_parameters_into_args(repository, platform) -> None:
    action = repository.create_action(
        name="A", kind="script", script_type="shell", path="/tmp/run.sh", args="--env ${env}"
    )
    executor, runner, _ = _make_executor(repository, platform)
    executor.execute(action, parameters={"env": "prod"})
    args = runner.call_args.args[0]
    assert args == ["/bin/zsh", "/tmp/run.sh", "--env", "prod"]


def test_script_missing_param_records_error(repository, platform) -> None:
    action = repository.create_action(
        name="A", kind="script", script_type="shell", path="${dir}/x.sh"
    )
    executor, runner, _ = _make_executor(repository, platform)
    result = executor.execute(action)
    assert result.ok is False and result.status == "error"
    assert result.missing_parameters == ["dir"]
    runner.assert_not_called()


def test_script_failure_records_exit_code(repository, platform) -> None:
    action = repository.create_action(name="A", kind="script", path="/x.sh")
    executor, _, _ = _make_executor(
        repository, platform, completed=FakeCompleted(returncode=2, stderr="boom")
    )
    result = executor.execute(action)
    assert result.status == "failed"
    runs = repository.list_runs()
    assert runs[0].exit_code == 2 and "退出码 2" in runs[0].message


def test_script_timeout_recorded(repository, platform) -> None:
    action = repository.create_action(name="A", kind="script", path="/x.sh", timeout_sec=1)

    def fake_run(argv, *, cwd, env, timeout, capture, on_started=None):
        raise subprocess.TimeoutExpired(argv, timeout, output="partial", stderr="")

    executor = QuickLaunchExecutor(repository, platform, subprocess_run=fake_run)
    result = executor.execute(action)
    assert result.status == "timeout"


def test_open_path_invokes_platform(repository, platform) -> None:
    action = repository.create_action(name="A", kind="open_path", path="${root}/file.txt")
    executor, _, _ = _make_executor(repository, platform)
    result = executor.execute(action, parameters={"root": "/tmp"})
    assert result.ok is True
    assert platform.open_path_calls == ["/tmp/file.txt"]


def test_open_url_invokes_platform(repository, platform) -> None:
    action = repository.create_action(name="A", kind="open_url", url="https://x.test/${q}")
    executor, _, _ = _make_executor(repository, platform)
    executor.execute(action, parameters={"q": "abc"})
    assert platform.open_url_calls == ["https://x.test/abc"]


def test_silent_feedback_skips_capture_and_no_notification(repository, platform) -> None:
    action = repository.create_action(
        name="A", kind="script", path="/x.sh", feedback_mode="silent"
    )
    executor, runner, notif = _make_executor(
        repository, platform, completed=FakeCompleted(returncode=0, stdout="loud")
    )
    executor.execute(action)
    _, kwargs = runner.call_args
    assert kwargs["capture"] is False
    runs = repository.list_runs()
    assert runs[0].stdout == ""
    notif.assert_not_called()


def test_notification_feedback_triggers_notification(repository, platform) -> None:
    action = repository.create_action(
        name="Build", kind="script", path="/x.sh", feedback_mode="notification"
    )
    executor, _, notif = _make_executor(repository, platform)
    executor.execute(action)
    notif.assert_called_once()
    kwargs = notif.call_args.kwargs
    assert kwargs["title"] == "Build"
    assert kwargs["success"] is True


def test_popup_feedback_captures_but_no_notification(repository, platform) -> None:
    action = repository.create_action(
        name="A", kind="script", path="/x.sh", feedback_mode="popup"
    )
    executor, runner, notif = _make_executor(
        repository, platform, completed=FakeCompleted(returncode=0, stdout="hi"),
    )
    result = executor.execute(action)
    _, kwargs = runner.call_args
    assert kwargs["capture"] is True
    assert result.feedback_mode == "popup"
    notif.assert_not_called()
    runs = repository.list_runs()
    assert runs[0].stdout == "hi"
