from __future__ import annotations

from pathlib import Path, PurePosixPath
import stat
from threading import RLock
import time
from typing import Callable, Protocol

from app.logging import get_logger

from .models import RemoteFileItem, RemoteProfile, join_remote_path, parent_remote_path


ProgressCallback = Callable[[int, int], None]
_LOG = None


def _logger():
    global _LOG
    if _LOG is None:
        _LOG = get_logger("features.remote_files.backends", plugin_id="remote-files")
    return _LOG


class RemoteBackend(Protocol):
    profile: RemoteProfile

    def connect(self) -> None:
        ...

    def close(self) -> None:
        ...

    def list_dir(self, path: str) -> list[RemoteFileItem]:
        ...

    def mkdir(self, path: str) -> None:
        ...

    def rename(self, source: str, target: str) -> None:
        ...

    def delete_file(self, path: str) -> None:
        ...

    def delete_dir(self, path: str) -> None:
        ...

    def upload_file(self, local_path: str, remote_path: str, progress: ProgressCallback | None = None) -> None:
        ...

    def download_file(self, remote_path: str, local_path: str, progress: ProgressCallback | None = None) -> None:
        ...

    def open_terminal(self):
        ...

    def home_dir(self) -> str:
        ...


class SftpBackend:
    def __init__(
        self,
        profile: RemoteProfile,
        *,
        ssh_client_factory=None,
        host_key_prompt: Callable[[dict], bool] | None = None,
        known_hosts_path: str | Path | None = None,
    ) -> None:
        self.profile = profile
        self._ssh_client_factory = ssh_client_factory
        self._host_key_prompt = host_key_prompt
        self._known_hosts_path = (
            Path(known_hosts_path) if known_hosts_path else None
        )
        self._ssh = None
        self._jump_ssh = None
        self._transport = None

    def connect(self) -> None:
        paramiko = _paramiko()
        factory = self._ssh_client_factory or paramiko.SSHClient
        sock = None
        if self.profile.jump_enabled:
            _logger().info(
                "remote_files.sftp.jump.connect_start",
                "开始连接 SFTP 跳板机",
                host=self.profile.jump_host,
                port=self.profile.jump_port,
                username=self.profile.jump_username or self.profile.username,
            )
            self._jump_ssh = factory()
            self._prepare_client(
                self._jump_ssh,
                host=self.profile.jump_host,
                port=self.profile.jump_port,
            )
            self._connect_client(
                self._jump_ssh,
                host=self.profile.jump_host,
                port=self.profile.jump_port,
                username=self.profile.jump_username or self.profile.username,
                password=self.profile.jump_password,
                key_path=self.profile.jump_private_key_path,
                passphrase=self.profile.jump_private_key_passphrase,
                use_agent=not bool(self.profile.jump_password or self.profile.jump_private_key_path),
            )
            jump_transport = self._jump_ssh.get_transport()
            if jump_transport is None:
                _logger().error("remote_files.sftp.jump.transport_missing", "跳板机 SSH transport 不可用", host=self.profile.jump_host)
                raise RuntimeError("跳板机 SSH transport 不可用")
            sock = jump_transport.open_channel(
                "direct-tcpip",
                (self.profile.host, self.profile.port),
                ("127.0.0.1", 0),
            )
            _logger().info(
                "remote_files.sftp.jump.connect_complete",
                "SFTP 跳板机连接完成",
                host=self.profile.jump_host,
                targetHost=self.profile.host,
                targetPort=self.profile.port,
            )

        _logger().info(
            "remote_files.sftp.connect_start",
            "开始连接 SFTP 目标服务器",
            host=self.profile.host,
            port=self.profile.port,
            username=self.profile.username,
            authKind=self.profile.auth_kind,
            viaJump=bool(sock),
        )
        self._ssh = factory()
        self._prepare_client(
            self._ssh,
            host=self.profile.host,
            port=self.profile.port,
        )
        self._connect_client(
            self._ssh,
            host=self.profile.host,
            port=self.profile.port,
            username=self.profile.username,
            password=self.profile.password,
            key_path=self.profile.private_key_path,
            passphrase=self.profile.private_key_passphrase,
            use_agent=self.profile.auth_kind == "agent",
            sock=sock,
        )
        self._transport = self._ssh.get_transport()
        if self._transport is None:
            _logger().error("remote_files.sftp.transport_missing", "SSH transport 不可用", host=self.profile.host)
            raise RuntimeError("SSH transport 不可用")
        _logger().info("remote_files.sftp.connect_complete", "SFTP 目标服务器连接完成", host=self.profile.host, port=self.profile.port)

    def close(self) -> None:
        _logger().info("remote_files.sftp.close", "关闭 SFTP 连接", host=self.profile.host)
        for client in (self._ssh, self._jump_ssh):
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass
        self._ssh = None
        self._jump_ssh = None
        self._transport = None

    def list_dir(self, path: str) -> list[RemoteFileItem]:
        _logger().debug("remote_files.sftp.list_dir", "读取 SFTP 目录", host=self.profile.host, remotePath=path)
        sftp = self._open_sftp()
        try:
            items: list[RemoteFileItem] = []
            for attr in sftp.listdir_attr(path):
                name = attr.filename
                if name in {".", ".."}:
                    continue
                mode = int(getattr(attr, "st_mode", 0) or 0)
                items.append(
                    RemoteFileItem(
                        name=name,
                        path=join_remote_path(path, name),
                        is_dir=stat.S_ISDIR(mode),
                        size=int(getattr(attr, "st_size", 0) or 0),
                        modified_at=int(getattr(attr, "st_mtime", 0) or 0),
                        permissions=stat.filemode(mode) if mode else "",
                    )
                )
            return sorted(items, key=lambda item: (not item.is_dir, item.name.lower()))
        finally:
            _close_quietly(sftp)

    def mkdir(self, path: str) -> None:
        _logger().info("remote_files.sftp.mkdir", "创建 SFTP 目录", host=self.profile.host, remotePath=path)
        sftp = self._open_sftp()
        try:
            sftp.mkdir(path)
        finally:
            _close_quietly(sftp)

    def rename(self, source: str, target: str) -> None:
        _logger().info("remote_files.sftp.rename", "重命名 SFTP 项目", host=self.profile.host, remotePath=source, targetPath=target)
        sftp = self._open_sftp()
        try:
            sftp.rename(source, target)
        finally:
            _close_quietly(sftp)

    def delete_file(self, path: str) -> None:
        _logger().info("remote_files.sftp.delete_file", "删除 SFTP 文件", host=self.profile.host, remotePath=path)
        sftp = self._open_sftp()
        try:
            sftp.remove(path)
        finally:
            _close_quietly(sftp)

    def delete_dir(self, path: str) -> None:
        _logger().info("remote_files.sftp.delete_dir", "删除 SFTP 目录", host=self.profile.host, remotePath=path)
        sftp = self._open_sftp()
        try:
            sftp.rmdir(path)
        finally:
            _close_quietly(sftp)

    def upload_file(self, local_path: str, remote_path: str, progress: ProgressCallback | None = None) -> None:
        _logger().info("remote_files.sftp.upload", "上传 SFTP 文件", host=self.profile.host, localPath=local_path, remotePath=remote_path)
        sftp = self._open_sftp()
        try:
            sftp.put(local_path, remote_path, callback=progress)
        finally:
            _close_quietly(sftp)

    def download_file(self, remote_path: str, local_path: str, progress: ProgressCallback | None = None) -> None:
        _logger().info("remote_files.sftp.download", "下载 SFTP 文件", host=self.profile.host, remotePath=remote_path, localPath=local_path)
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        sftp = self._open_sftp()
        try:
            sftp.get(remote_path, local_path, callback=progress)
        finally:
            _close_quietly(sftp)

    def open_terminal(self):
        if self._ssh is None:
            raise RuntimeError("SFTP 连接未建立")
        _logger().info("remote_files.sftp.terminal.open", "打开 SFTP 共享 SSH 终端", host=self.profile.host)
        return self._ssh.invoke_shell(term="xterm-256color")

    def home_dir(self) -> str:
        sftp = self._open_sftp()
        try:
            try:
                home = sftp.normalize(".")
            except Exception:
                home = "/"
            return home if home and home.startswith("/") else "/"
        finally:
            _close_quietly(sftp)

    def _open_sftp(self):
        if self._transport is None:
            raise RuntimeError("SFTP 连接未建立")
        paramiko = _paramiko()
        return paramiko.SFTPClient.from_transport(self._transport)

    def _prepare_client(self, client, *, host: str, port: int) -> None:
        paramiko = _paramiko()
        client.load_system_host_keys()
        if self._host_key_prompt is not None:
            policy_cls = _prompting_policy_class()
            client.set_missing_host_key_policy(
                policy_cls(
                    self._host_key_prompt,
                    host=host,
                    port=int(port),
                    known_hosts_path=self._known_hosts_path,
                )
            )
        else:
            client.set_missing_host_key_policy(paramiko.RejectPolicy())

    def _connect_client(
        self,
        client,
        *,
        host: str,
        port: int,
        username: str,
        password: str = "",
        key_path: str = "",
        passphrase: str = "",
        use_agent: bool = False,
        sock=None,
    ) -> None:
        kwargs = {
            "hostname": host,
            "port": int(port),
            "username": username or None,
            "timeout": self.profile.connect_timeout,
            "banner_timeout": self.profile.connect_timeout,
            "auth_timeout": self.profile.connect_timeout,
            "sock": sock,
            "look_for_keys": use_agent,
            "allow_agent": use_agent,
        }
        if key_path:
            kwargs["key_filename"] = key_path
            kwargs["passphrase"] = passphrase or None
        elif password:
            kwargs["password"] = password
        kwargs["transport_factory"] = _legacy_compatible_transport
        client.connect(**kwargs)


class FtpBackend:
    def __init__(self, profile: RemoteProfile, *, ftp_factory=None, ftps_factory=None) -> None:
        self.profile = profile
        self._ftp_factory = ftp_factory
        self._ftps_factory = ftps_factory
        self._ftp = None
        self._lock = RLock()
        self._log_sink = None

    def set_log_sink(self, sink) -> None:
        """Register a ``callable(str)`` that receives every FTP debug line.

        Lines look like ``*cmd* CWD /foo`` or ``*resp* 250 OK``. The
        ``ftplib.FTP.sanitize`` helper already masks passwords. Set before
        ``connect()`` so login traffic is captured too.
        """

        self._log_sink = sink

    def connect(self) -> None:
        import ftplib

        with self._lock:
            if self.profile.protocol == "ftps":
                factory = self._ftps_factory or ftplib.FTP_TLS
            else:
                factory = self._ftp_factory or ftplib.FTP
            _logger().info(
                "remote_files.ftp.connect_start",
                "开始连接 FTP/FTPS 服务器",
                protocol=self.profile.protocol,
                host=self.profile.host,
                port=self.profile.port,
                username=self.profile.username,
            )
            self._ftp = factory()
            if self.profile.encoding:
                self._ftp.encoding = self.profile.encoding
            self._ftp_call(
                f"CONNECT {self.profile.host}:{self.profile.port}",
                self._ftp.connect,
                self.profile.host,
                self.profile.port,
                timeout=self.profile.connect_timeout,
            )
            self._ftp_call(
                f"USER {self.profile.username}",
                self._ftp.login,
                self.profile.username,
                self.profile.password,
            )
            self._emit_log(f"> PASV {'on' if self.profile.passive_mode else 'off'}")
            self._ftp.set_pasv(self.profile.passive_mode)
            if self.profile.protocol == "ftps" and hasattr(self._ftp, "prot_p"):
                self._ftp_call("PROT P", self._ftp.prot_p)
            _logger().info(
                "remote_files.ftp.connect_complete",
                "FTP/FTPS 服务器连接完成",
                protocol=self.profile.protocol,
                host=self.profile.host,
                port=self.profile.port,
                passiveMode=self.profile.passive_mode,
            )

    def close(self) -> None:
        _logger().info("remote_files.ftp.close", "关闭 FTP/FTPS 连接", protocol=self.profile.protocol, host=self.profile.host)
        with self._lock:
            ftp = self._ftp
            self._ftp = None
        if ftp is None:
            return
        try:
            self._ftp_call("QUIT", ftp.quit)
        except Exception:
            try:
                ftp.close()
            except Exception:
                pass

    def list_dir(self, path: str) -> list[RemoteFileItem]:
        with self._lock:
            ftp = self._require_ftp()
            try:
                self._emit_log(f"> MLSD {path}")
                entries = list(ftp.mlsd(path))
                self._emit_log(f"< MLSD {len(entries)} entries")
                return sorted(
                    [self._item_from_mlsd(path, name, facts) for name, facts in entries if name not in {".", ".."}],
                    key=lambda item: (not item.is_dir, item.name.lower()),
                )
            except Exception as exc:
                _logger().warning(
                    "remote_files.ftp.list_mlsd_failed",
                    "MLSD 读取失败，切换到 LIST fallback",
                    protocol=self.profile.protocol,
                    host=self.profile.host,
                    remotePath=path,
                    error=str(exc),
                )
                self._emit_log(f"< MLSD unsupported ({exc}); fallback to LIST")
                lines: list[str] = []
                cmd = f"LIST {path}" if path else "LIST"
                self._emit_log(f"> {cmd}")
                ftp.retrlines(cmd, lines.append)
                self._emit_log(f"< LIST {len(lines)} lines")
                items: list[RemoteFileItem] = []
                for line in lines:
                    parsed = _parse_list_line(line)
                    if parsed is None:
                        continue
                    name, is_dir, size, mtime = parsed
                    if name in {".", "..", ""}:
                        continue
                    items.append(
                        RemoteFileItem(
                            name=name,
                            path=join_remote_path(path, name),
                            is_dir=is_dir,
                            size=0 if is_dir else size,
                            modified_at=mtime,
                        )
                    )
                return sorted(items, key=lambda item: (not item.is_dir, item.name.lower()))

    def mkdir(self, path: str) -> None:
        with self._lock:
            _logger().info("remote_files.ftp.mkdir", "创建 FTP/FTPS 目录", protocol=self.profile.protocol, host=self.profile.host, remotePath=path)
            self._ftp_call(f"MKD {path}", self._require_ftp().mkd, path)

    def rename(self, source: str, target: str) -> None:
        with self._lock:
            _logger().info("remote_files.ftp.rename", "重命名 FTP/FTPS 项目", protocol=self.profile.protocol, host=self.profile.host, remotePath=source, targetPath=target)
            self._ftp_call(f"RNFR {source} -> {target}", self._require_ftp().rename, source, target)

    def delete_file(self, path: str) -> None:
        with self._lock:
            _logger().info("remote_files.ftp.delete_file", "删除 FTP/FTPS 文件", protocol=self.profile.protocol, host=self.profile.host, remotePath=path)
            self._ftp_call(f"DELE {path}", self._require_ftp().delete, path)

    def delete_dir(self, path: str) -> None:
        with self._lock:
            _logger().info("remote_files.ftp.delete_dir", "删除 FTP/FTPS 目录", protocol=self.profile.protocol, host=self.profile.host, remotePath=path)
            self._ftp_call(f"RMD {path}", self._require_ftp().rmd, path)

    def upload_file(self, local_path: str, remote_path: str, progress: ProgressCallback | None = None) -> None:
        with self._lock:
            _logger().info("remote_files.ftp.upload", "上传 FTP/FTPS 文件", protocol=self.profile.protocol, host=self.profile.host, localPath=local_path, remotePath=remote_path)
            ftp = self._require_ftp()
            total = Path(local_path).stat().st_size
            sent = 0

            def callback(block: bytes) -> None:
                nonlocal sent
                sent += len(block)
                if progress is not None:
                    progress(sent, total)

            self._emit_log(f"> STOR {remote_path}")
            with Path(local_path).open("rb") as file_obj:
                try:
                    ftp.storbinary(f"STOR {remote_path}", file_obj, blocksize=64 * 1024, callback=callback)
                except Exception as exc:
                    self._emit_log(f"! STOR {remote_path}: {exc}")
                    raise
            self._emit_log(f"< STOR {sent} bytes")

    def download_file(self, remote_path: str, local_path: str, progress: ProgressCallback | None = None) -> None:
        with self._lock:
            _logger().info("remote_files.ftp.download", "下载 FTP/FTPS 文件", protocol=self.profile.protocol, host=self.profile.host, remotePath=remote_path, localPath=local_path)
            ftp = self._require_ftp()
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            try:
                total = int(ftp.size(remote_path) or 0)
            except Exception:
                total = 0
            received = 0
            self._emit_log(f"> RETR {remote_path}")
            with Path(local_path).open("wb") as file_obj:

                def callback(block: bytes) -> None:
                    nonlocal received
                    file_obj.write(block)
                    received += len(block)
                    if progress is not None:
                        progress(received, total)

                try:
                    ftp.retrbinary(f"RETR {remote_path}", callback, blocksize=64 * 1024)
                except Exception as exc:
                    self._emit_log(f"! RETR {remote_path}: {exc}")
                    raise
            self._emit_log(f"< RETR {received} bytes")

    def open_terminal(self):
        raise RuntimeError("FTP/FTPS 不支持 SSH 终端")

    def home_dir(self) -> str:
        with self._lock:
            try:
                value = str(self._ftp_call("PWD", self._require_ftp().pwd) or "/")
            except Exception:
                value = "/"
            if not value.startswith("/"):
                value = "/" + value
            return value

    def _require_ftp(self):
        if self._ftp is None:
            raise RuntimeError("FTP 连接未建立")
        return self._ftp

    def _item_from_mlsd(self, path: str, name: str, facts: dict) -> RemoteFileItem:
        item_type = str(facts.get("type") or "").lower()
        return RemoteFileItem(
            name=name,
            path=join_remote_path(path, name),
            is_dir=item_type == "dir",
            size=_safe_int(facts.get("size"), 0),
            modified_at=_parse_ftp_modify(facts.get("modify")),
            permissions=str(facts.get("perm") or ""),
        )

    def _emit_log(self, line: str) -> None:
        sink = self._log_sink
        if sink is not None:
            try:
                sink(line)
            except Exception:
                pass
        _logger().debug("remote_files.ftp.io", line, protocol=self.profile.protocol, host=self.profile.host)

    def _ftp_call(self, label: str, fn, *args, **kwargs):
        self._emit_log(f"> {label}")
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:
            self._emit_log(f"! {label}: {exc}")
            raise
        if isinstance(result, str) and result:
            self._emit_log(f"< {result}")
        else:
            self._emit_log(f"< {label} ok")
        return result


def create_backend(
    profile: RemoteProfile,
    *,
    host_key_prompt: Callable[[dict], bool] | None = None,
    known_hosts_path: str | Path | None = None,
) -> RemoteBackend:
    if profile.protocol == "sftp":
        return SftpBackend(
            profile,
            host_key_prompt=host_key_prompt,
            known_hosts_path=known_hosts_path,
        )
    return FtpBackend(profile)


def remote_target_for_rename(source: str, new_name: str) -> str:
    return join_remote_path(parent_remote_path(source), new_name)


def _paramiko():
    import paramiko

    return paramiko


_LEGACY_HOST_KEY_ALGORITHMS = ("ssh-rsa",)
_LEGACY_PATCHED = False


def _enable_legacy_ssh_rsa(paramiko) -> None:
    """Restore ssh-rsa (RSA + SHA-1) support that paramiko 5 dropped.

    Why: paramiko 5 removed ssh-rsa from preferred host key algorithms,
    Transport._key_info, and RSAKey.HASHES. Older OpenSSH servers that only
    sign with ssh-rsa surface as 'Incompatible ssh peer (no acceptable host
    key)' or 'unknown cipher'. Re-adding the entries keeps modern servers on
    sha2 (those names come first) while letting legacy servers negotiate.
    """
    global _LEGACY_PATCHED
    if _LEGACY_PATCHED:
        return
    from cryptography.hazmat.primitives import hashes

    rsa_key = paramiko.RSAKey
    if "ssh-rsa" not in rsa_key.HASHES:
        rsa_key.HASHES["ssh-rsa"] = hashes.SHA1
    transport_cls = paramiko.Transport
    if "ssh-rsa" not in transport_cls._key_info:
        transport_cls._key_info["ssh-rsa"] = rsa_key
    _LEGACY_PATCHED = True


def _legacy_compatible_transport(sock, *, disabled_algorithms=None):
    """Build a paramiko Transport that also accepts legacy ssh-rsa host keys."""
    paramiko = _paramiko()
    _enable_legacy_ssh_rsa(paramiko)
    transport = paramiko.Transport(sock, disabled_algorithms=disabled_algorithms)
    for attr in ("_preferred_keys", "_preferred_pubkeys"):
        current = tuple(getattr(transport, attr, ()))
        extras = tuple(a for a in _LEGACY_HOST_KEY_ALGORITHMS if a not in current)
        if extras:
            setattr(transport, attr, current + extras)
    return transport


_PROMPTING_POLICY_CLS = None


def _prompting_policy_class():
    global _PROMPTING_POLICY_CLS
    if _PROMPTING_POLICY_CLS is not None:
        return _PROMPTING_POLICY_CLS
    paramiko = _paramiko()

    class PromptingHostKeyPolicy(paramiko.MissingHostKeyPolicy):
        def __init__(
            self,
            prompt: Callable[[dict], bool],
            *,
            host: str,
            port: int,
            known_hosts_path: Path | None = None,
        ) -> None:
            self._prompt = prompt
            self._host = host
            self._port = int(port)
            self._known_hosts_path = (
                Path(known_hosts_path)
                if known_hosts_path
                else Path.home() / ".ssh" / "known_hosts"
            )

        def missing_host_key(self, client, hostname, key) -> None:
            info = {
                "host": self._host,
                "port": self._port,
                "keyType": key.get_name(),
                "fingerprintSha256": _format_fingerprint_sha256(key),
                "fingerprintMd5": _format_fingerprint_md5(key),
            }
            accepted = False
            try:
                accepted = bool(self._prompt(info))
            except Exception as exc:
                raise _paramiko().SSHException(
                    f"主机指纹确认失败: {exc}"
                ) from exc
            if not accepted:
                raise _paramiko().SSHException("用户拒绝了主机指纹")
            client.get_host_keys().add(hostname, key.get_name(), key)
            _persist_host_key(self._known_hosts_path, hostname, key)

    _PROMPTING_POLICY_CLS = PromptingHostKeyPolicy
    return _PROMPTING_POLICY_CLS


def _format_fingerprint_sha256(key) -> str:
    import base64
    import hashlib

    digest = hashlib.sha256(key.asbytes()).digest()
    return "SHA256:" + base64.b64encode(digest).rstrip(b"=").decode("ascii")


def _format_fingerprint_md5(key) -> str:
    import hashlib

    digest = hashlib.md5(key.asbytes()).hexdigest()
    return "MD5:" + ":".join(digest[i : i + 2] for i in range(0, len(digest), 2))


def _persist_host_key(path: Path, hostname: str, key) -> None:
    paramiko = _paramiko()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    host_keys = paramiko.HostKeys()
    if path.exists():
        try:
            host_keys.load(str(path))
        except Exception:
            pass
    host_keys.add(hostname, key.get_name(), key)
    host_keys.save(str(path))
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _close_quietly(obj) -> None:
    try:
        obj.close()
    except Exception:
        pass


def _safe_int(value: object, default: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _parse_ftp_modify(value: object) -> int:
    text = str(value or "").strip()
    if len(text) < 14:
        return 0
    try:
        return int(time.mktime(time.strptime(text[:14], "%Y%m%d%H%M%S")))
    except ValueError:
        return 0


_LIST_MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def _parse_list_line(line: str) -> tuple[str, bool, int, int] | None:
    """Parse one line of Unix-style FTP `LIST` output.

    Returns (name, is_dir, size_bytes, mtime_epoch) or None for unparseable
    lines. Format example:
        drwxr-xr-x  2 root root 4096 May  1 12:00 dirname
        -rw-r--r--  1 root root  123 May  1  2024 filename
        lrwxrwxrwx  1 root root    7 May  1 12:00 link -> target
    Symlinks are reported as files; the ' -> target' suffix is stripped.
    """
    text = str(line or "").rstrip()
    if not text:
        return None
    parts = text.split(None, 8)
    if len(parts) < 9:
        return None
    perms = parts[0]
    if not perms or perms[0] not in {"d", "-", "l", "c", "b", "s", "p"}:
        return None
    is_dir = perms.startswith("d")
    size = _safe_int(parts[4], 0)
    month = _LIST_MONTHS.get(parts[5])
    if month is None:
        return None
    day = _safe_int(parts[6], 0)
    time_or_year = parts[7]
    name = parts[8]
    if perms.startswith("l"):
        arrow = name.find(" -> ")
        if arrow != -1:
            name = name[:arrow]
    mtime = _list_line_mtime(month, day, time_or_year)
    return name, is_dir, size, mtime


def _list_line_mtime(month: int, day: int, time_or_year: str) -> int:
    text = str(time_or_year or "")
    now = time.localtime()
    try:
        if ":" in text:
            hour_str, minute_str = text.split(":", 1)
            year = now.tm_year
            struct = time.struct_time(
                (year, month, day, int(hour_str), int(minute_str), 0, 0, 0, -1)
            )
            epoch = int(time.mktime(struct))
            now_epoch = int(time.mktime(now))
            if epoch - now_epoch > 86400:
                struct = time.struct_time(
                    (year - 1, month, day, int(hour_str), int(minute_str), 0, 0, 0, -1)
                )
                epoch = int(time.mktime(struct))
            return epoch
        year = int(text)
        return int(time.mktime(time.struct_time((year, month, day, 0, 0, 0, 0, 0, -1))))
    except (ValueError, OverflowError):
        return 0
