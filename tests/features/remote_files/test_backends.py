from __future__ import annotations

from pathlib import Path

import pytest

from features.remote_files.backends import (
    FtpBackend,
    SftpBackend,
    _parse_list_line,
    _prompting_policy_class,
)
from features.remote_files.models import RemoteProfile


class FakeTransport:
    def __init__(self) -> None:
        self.opened_channels = []

    def open_channel(self, kind, destination, source):
        self.opened_channels.append((kind, destination, source))
        return "jump-socket"


class FakeShell:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeSSHClient:
    instances = []

    def __init__(self) -> None:
        self.transport = FakeTransport()
        self.connect_kwargs = None
        self.shell = FakeShell()
        FakeSSHClient.instances.append(self)

    def load_system_host_keys(self) -> None:
        pass

    def set_missing_host_key_policy(self, policy) -> None:
        self.policy = policy

    def connect(self, **kwargs) -> None:
        self.connect_kwargs = kwargs

    def get_transport(self):
        return self.transport

    def invoke_shell(self, **kwargs):
        self.shell_kwargs = kwargs
        return self.shell

    def close(self) -> None:
        self.closed = True


class FakeFTP:
    def __init__(self) -> None:
        self.commands = []
        self.encoding = ""
        self.cwd_path = "/"
        self.files = {"/remote/a.txt": b"abc"}
        self.list_lines: list[str] = [
            "drwxr-xr-x  2 root root 4096 May  1 12:00 dir",
            "-rw-r--r--  1 root root    3 May  1 12:00 a.txt",
        ]
        self.mlsd_raises = True
        self.fail_command: str | None = None

    def connect(self, host, port, timeout):
        self.commands.append(("connect", host, port, timeout))
        return "220 ready"

    def login(self, username, password):
        self.commands.append(("login", username, password))
        return "230 ok"

    def set_pasv(self, passive):
        self.commands.append(("pasv", passive))

    def mlsd(self, path):
        if self.mlsd_raises:
            raise RuntimeError("mlsd unsupported")
        return [("a.txt", {"type": "file", "size": "3"})]

    def retrlines(self, command, callback):
        self.commands.append(("retrlines", command))
        for line in self.list_lines:
            callback(line)

    def pwd(self):
        if self.fail_command == "pwd":
            raise RuntimeError("pwd boom")
        return self.cwd_path

    def cwd(self, path):
        if path.endswith("/dir"):
            self.cwd_path = path
            return
        raise RuntimeError("not dir")

    def size(self, path):
        return len(self.files.get(path, b""))

    def sendcmd(self, command):
        return "213 20250102030405"

    def mkd(self, path):
        self.commands.append(("mkd", path))
        return "257 created"

    def rename(self, source, target):
        if self.fail_command == "rename":
            raise RuntimeError("rename boom")
        self.commands.append(("rename", source, target))

    def delete(self, path):
        self.commands.append(("delete", path))

    def rmd(self, path):
        self.commands.append(("rmd", path))

    def storbinary(self, command, file_obj, blocksize, callback):
        block = file_obj.read()
        callback(block)
        self.commands.append(("stor", command, block))

    def retrbinary(self, command, callback, blocksize):
        callback(b"abc")
        self.commands.append(("retr", command))

    def quit(self):
        self.commands.append(("quit",))


def test_sftp_backend_uses_jump_host_direct_tcpip(monkeypatch) -> None:
    class FakeParamiko:
        SSHClient = FakeSSHClient

        class AutoAddPolicy:
            pass

        class RejectPolicy:
            pass

        class SFTPClient:
            @staticmethod
            def from_transport(transport):
                return object()

    FakeSSHClient.instances = []
    monkeypatch.setattr("features.remote_files.backends._paramiko", lambda: FakeParamiko)
    profile = RemoteProfile(
        protocol="sftp",
        host="target.example.com",
        username="alice",
        password="secret",
        jump_enabled=True,
        jump_host="jump.example.com",
        jump_username="jump",
        jump_password="jump-secret",
    )

    backend = SftpBackend(profile, ssh_client_factory=FakeSSHClient)
    backend.connect()
    shell = backend.open_terminal()

    jump_client, target_client = FakeSSHClient.instances
    assert jump_client.connect_kwargs["hostname"] == "jump.example.com"
    assert jump_client.transport.opened_channels[0][0] == "direct-tcpip"
    assert jump_client.transport.opened_channels[0][1] == ("target.example.com", 22)
    assert target_client.connect_kwargs["sock"] == "jump-socket"
    assert target_client.shell_kwargs["term"] == "xterm-256color"
    assert shell is target_client.shell


def test_ftp_backend_lists_with_list_fallback_and_transfers(tmp_path: Path) -> None:
    ftp = FakeFTP()
    log_lines = []
    profile = RemoteProfile(protocol="ftp", host="ftp.example.com", username="u", password="p")
    backend = FtpBackend(profile, ftp_factory=lambda: ftp)
    backend.set_log_sink(log_lines.append)
    backend.connect()

    items = backend.list_dir("/remote")

    assert [item.name for item in items] == ["dir", "a.txt"]
    assert items[0].is_dir is True
    assert items[1].size == 3
    # LIST fallback runs in one round-trip rather than per-item probes
    assert ("retrlines", "LIST /remote") in ftp.commands
    assert any("fallback to LIST" in line for line in log_lines)
    assert not any(line.startswith("! MLSD") for line in log_lines)

    local = tmp_path / "upload.txt"
    local.write_bytes(b"hello")
    progress = []
    backend.upload_file(str(local), "/remote/upload.txt", lambda done, total: progress.append((done, total)))
    assert progress[-1] == (5, 5)

    target = tmp_path / "download.txt"
    backend.download_file("/remote/a.txt", str(target))
    assert target.read_bytes() == b"abc"


def _make_test_key():
    import paramiko

    return paramiko.RSAKey.generate(bits=1024)


class _RecordingHostKeys:
    def __init__(self) -> None:
        self.added: list[tuple[str, str, object]] = []

    def add(self, hostname, keytype, key) -> None:
        self.added.append((hostname, keytype, key))


class _StubClient:
    def __init__(self) -> None:
        self._keys = _RecordingHostKeys()

    def get_host_keys(self):
        return self._keys


def test_prompting_policy_persists_accepted_key(tmp_path: Path) -> None:
    known_hosts = tmp_path / "known_hosts"
    captured: dict = {}

    def prompt(info: dict) -> bool:
        captured.update(info)
        return True

    cls = _prompting_policy_class()
    policy = cls(prompt, host="target.example.com", port=2222, known_hosts_path=known_hosts)
    client = _StubClient()
    key = _make_test_key()

    policy.missing_host_key(client, "target.example.com", key)

    assert captured["host"] == "target.example.com"
    assert captured["port"] == 2222
    assert captured["keyType"] == key.get_name()
    assert captured["fingerprintSha256"].startswith("SHA256:")
    assert captured["fingerprintMd5"].startswith("MD5:")
    assert client._keys.added == [("target.example.com", key.get_name(), key)]
    assert known_hosts.exists()
    assert "target.example.com" in known_hosts.read_text()


def test_prompting_policy_rejects_with_ssh_exception(tmp_path: Path) -> None:
    import paramiko

    known_hosts = tmp_path / "known_hosts"

    def prompt(info: dict) -> bool:
        return False

    cls = _prompting_policy_class()
    policy = cls(prompt, host="target.example.com", port=22, known_hosts_path=known_hosts)
    client = _StubClient()
    key = _make_test_key()

    with pytest.raises(paramiko.SSHException, match="拒绝"):
        policy.missing_host_key(client, "target.example.com", key)

    assert client._keys.added == []
    assert not known_hosts.exists()


def test_parse_list_line_handles_unix_listing() -> None:
    dir_entry = _parse_list_line("drwxr-xr-x  2 root root 4096 May  1 12:00 dirname")
    assert dir_entry is not None
    name, is_dir, size, _mtime = dir_entry
    assert (name, is_dir, size) == ("dirname", True, 4096)

    file_entry = _parse_list_line("-rw-r--r--  1 root root  123 May  1  2024 filename")
    assert file_entry is not None
    name, is_dir, size, _mtime = file_entry
    assert (name, is_dir, size) == ("filename", False, 123)

    symlink = _parse_list_line("lrwxrwxrwx  1 root root    7 May  1 12:00 link -> target")
    assert symlink is not None
    assert symlink[0] == "link"
    assert symlink[1] is False

    assert _parse_list_line("") is None
    assert _parse_list_line("total 8") is None


def test_ftp_call_logs_request_and_response_to_sink() -> None:
    ftp = FakeFTP()
    profile = RemoteProfile(protocol="ftp", host="ftp.example.com", port=21, username="u", password="p")
    backend = FtpBackend(profile, ftp_factory=lambda: ftp)
    captured: list[str] = []
    backend.set_log_sink(captured.append)
    backend.connect()

    joined = " | ".join(captured)
    assert "> CONNECT ftp.example.com:21" in joined
    assert "< 220 ready" in joined
    assert "> USER u" in joined
    assert "< 230 ok" in joined


def test_ftp_call_logs_failure_and_reraises() -> None:
    ftp = FakeFTP()
    ftp.fail_command = "rename"
    profile = RemoteProfile(protocol="ftp", host="ftp.example.com", username="u", password="p")
    backend = FtpBackend(profile, ftp_factory=lambda: ftp)
    captured: list[str] = []
    backend.set_log_sink(captured.append)
    backend.connect()

    with pytest.raises(RuntimeError, match="rename boom"):
        backend.rename("/a", "/b")

    assert any("! RNFR /a -> /b: rename boom" in line for line in captured)
