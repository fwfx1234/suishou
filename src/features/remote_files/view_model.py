from __future__ import annotations

from pathlib import Path
import threading

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QGuiApplication

from app.concurrency import PythonTaskRunner
from app.logging import get_logger
from app.storage import SQLiteDatabase

from .service import RemoteFilesService, is_editable_file_item


class RemoteFilesViewModel(QObject):
    profilesChanged = Signal()
    sessionsChanged = Signal()
    activeProfileIdChanged = Signal()
    connectionStateChanged = Signal()
    localPathChanged = Signal()
    remotePathChanged = Signal()
    localItemsChanged = Signal()
    remoteItemsChanged = Signal()
    transfersChanged = Signal()
    statusMessageChanged = Signal()
    terminalBridgeChanged = Signal()
    ftpLogChanged = Signal()
    ftpLogCopied = Signal(bool, str)
    hostKeyPromptRequested = Signal("QVariantMap")
    editedFileUploadRequested = Signal("QVariantMap")
    _uiCallback = Signal(object)

    def __init__(self, database: SQLiteDatabase, platform_api: object | None = None) -> None:
        super().__init__()
        self._log = get_logger("features.remote_files.view_model", plugin_id="remote-files")
        self._disposed = False
        self._platform = platform_api
        self._uiCallback.connect(self._run_ui_callback)
        self._runner = PythonTaskRunner(max_workers=4, thread_name_prefix="remote-files")
        self._profiles: list[dict] = []
        self._host_key_lock = threading.Lock()
        self._pending_host_key_prompts: dict[str, tuple[threading.Event, list[bool]]] = {}
        self._service = RemoteFilesService(
            database,
            on_transfers_updated=lambda pid, items: self._post_ui(lambda: self._on_transfers(pid, items)),
            on_message=lambda pid, message: self._post_ui(lambda: self._on_message(pid, message)),
            on_ftp_log=lambda pid, line: self._post_ui(lambda: self._on_ftp_log(pid, line)),
            on_snapshot_changed=lambda pid: self._post_ui(lambda: self._on_snapshot_changed(pid)),
            host_key_prompt=self._prompt_host_key,
        )
        self._profiles = self._service.list_profiles()
        self._log.info("remote_files.viewmodel.ready", "远程文件插件 ViewModel 已初始化", profileCount=len(self._profiles))
        self._pending_terminal_sync = False
        self._bound_bridges: set[int] = set()
        self._upload_refresh_pending: dict[str, set[str]] = {}
        self._upload_refresh_refreshed: dict[str, set[str]] = {}
        self._edit_sessions: dict[str, dict] = {}
        self._edit_poll_timer = QTimer(self)
        self._edit_poll_timer.setInterval(1200)
        self._edit_poll_timer.timeout.connect(self._check_file_edit_sessions)

    # ------------------------ properties -------------------------------

    profiles = Property("QVariantList", lambda self: self._profiles, notify=profilesChanged)
    sessions = Property("QVariantList", lambda self: self._service.sessions_summary(), notify=sessionsChanged)
    activeProfileId = Property(str, lambda self: self._service.active_profile_id(), notify=activeProfileIdChanged)
    connectionState = Property("QVariantMap", lambda self: self._active_snapshot(), notify=connectionStateChanged)
    localPath = Property(str, lambda self: self._service.local_path_for(self._service.active_profile_id()), notify=localPathChanged)
    remotePath = Property(str, lambda self: self._service.remote_path_for(self._service.active_profile_id()), notify=remotePathChanged)
    localItems = Property("QVariantList", lambda self: self._service.local_items_for(self._service.active_profile_id()), notify=localItemsChanged)
    remoteItems = Property("QVariantList", lambda self: self._service.remote_items_for(self._service.active_profile_id()), notify=remoteItemsChanged)
    transfers = Property("QVariantList", lambda self: self._service.transfers_for(self._service.active_profile_id()), notify=transfersChanged)
    statusMessage = Property(str, lambda self: self._active_snapshot().get("message", ""), notify=statusMessageChanged)
    terminalBridge = Property(QObject, lambda self: self._service.terminal_bridge_for(self._service.active_profile_id()), notify=terminalBridgeChanged)
    ftpLog = Property("QVariantList", lambda self: self._service.ftp_log_for(self._service.active_profile_id()), notify=ftpLogChanged)

    def _active_snapshot(self) -> dict:
        pid = self._service.active_profile_id()
        if pid:
            return self._service.snapshot_for(pid)
        return {"status": "disconnected", "profileId": "", "protocol": "", "host": "", "message": ""}

    # ------------------------ slots: profiles --------------------------

    @Slot()
    def reloadProfiles(self) -> None:
        self._log.debug("remote_files.profiles.reload", "重新加载远程连接配置")
        self._profiles = self._service.list_profiles()
        self.profilesChanged.emit()

    @Slot("QVariantMap")
    def saveProfile(self, payload) -> None:
        data = dict(payload or {})
        self._log.info(
            "remote_files.profile.save_requested",
            "保存远程连接配置请求",
            profileId=str(data.get("id") or ""),
            protocol=str(data.get("protocol") or ""),
            host=str(data.get("host") or ""),
        )
        self._run_background(
            lambda: self._service.save_profile(data),
            on_success=lambda profiles: self._set_profiles(profiles),
        )

    @Slot(str)
    def deleteProfile(self, profileId: str) -> None:
        self._log.info("remote_files.profile.delete_requested", "删除远程连接配置请求", profileId=profileId)
        self._run_background(
            lambda: self._service.delete_profile(profileId),
            on_success=lambda profiles: (self._set_profiles(profiles), self._emit_all_active_changed()),
        )

    # ------------------------ slots: sessions --------------------------

    @Slot(str)
    def setActiveProfile(self, profileId: str) -> None:
        target = str(profileId or "")
        if target == self._service.active_profile_id():
            return
        if target and not self._service.has_session(target):
            self._service.set_active(target)
            self.activeProfileIdChanged.emit()
            self._emit_all_active_changed()
            return
        self._service.set_active(target)
        self.activeProfileIdChanged.emit()
        self._bind_terminal_bridge_for(target)
        self._emit_all_active_changed()

    @Slot(str)
    def connectProfile(self, profileId: str) -> None:
        self._log.info("remote_files.connect.requested", "连接请求", profileId=profileId)
        self._service.set_active(profileId)
        try:
            self._service.prepare_session(profileId)
        except Exception as exc:
            self.activeProfileIdChanged.emit()
            self._handle_error(exc)
            return
        self.activeProfileIdChanged.emit()
        self.sessionsChanged.emit()
        self._run_background(
            lambda: self._service.connect(profileId),
            on_success=lambda _result: (
                self._bind_terminal_bridge_for(profileId),
                self.sessionsChanged.emit(),
                self._emit_all_active_changed(),
                self.reloadProfiles(),
                self._auto_open_terminal(profileId),
            ),
        )

    def _auto_open_terminal(self, profile_id: str) -> None:
        snapshot = self._service.snapshot_for(profile_id)
        if (snapshot.get("protocol") or "").lower() != "sftp":
            return
        bridge = self._service.terminal_bridge_for(profile_id)
        if bridge is not None and hasattr(bridge, "is_attached") and bridge.is_attached():
            return
        self._run_background(
            lambda: self._service.open_terminal(profile_id),
            on_success=lambda _: (
                self._bind_terminal_bridge_for(profile_id),
                self.terminalBridgeChanged.emit(),
            ),
        )

    @Slot(str, bool)
    def respondHostKeyPrompt(self, profileId: str, accepted: bool) -> None:
        key = str(profileId or "")
        with self._host_key_lock:
            entry = self._pending_host_key_prompts.pop(key, None)
        if entry is None:
            return
        event, result = entry
        result[0] = bool(accepted)
        event.set()
        self._log.info(
            "remote_files.host_key.user_response",
            "用户已回复主机指纹确认",
            profileId=key,
            accepted=bool(accepted),
        )

    def _prompt_host_key(self, info: dict) -> bool:
        profile_id = str(info.get("profileId") or "")
        if not profile_id or self._disposed:
            return False
        event = threading.Event()
        result = [False]
        with self._host_key_lock:
            self._pending_host_key_prompts[profile_id] = (event, result)
        try:
            self._log.info(
                "remote_files.host_key.prompt",
                "等待用户确认主机指纹",
                profileId=profile_id,
                host=str(info.get("host") or ""),
                port=int(info.get("port") or 0),
                keyType=str(info.get("keyType") or ""),
                fingerprintSha256=str(info.get("fingerprintSha256") or ""),
            )
            self._post_ui(lambda: self.hostKeyPromptRequested.emit(info))
            if not event.wait(timeout=120):
                self._log.warning(
                    "remote_files.host_key.timeout",
                    "主机指纹确认超时，按拒绝处理",
                    profileId=profile_id,
                )
                return False
            return bool(result[0])
        finally:
            with self._host_key_lock:
                self._pending_host_key_prompts.pop(profile_id, None)

    @Slot()
    def disconnect(self) -> None:
        self.disconnectProfile(self._service.active_profile_id())

    @Slot(str)
    def disconnectProfile(self, profileId: str) -> None:
        target = str(profileId or "") or self._service.active_profile_id()
        if not target:
            return
        self._log.info("remote_files.disconnect.requested", "断开连接请求", profileId=target)
        self._run_background(
            lambda: self._service.disconnect(target),
            on_success=lambda _: (self.sessionsChanged.emit(), self.activeProfileIdChanged.emit(), self._emit_all_active_changed()),
        )

    @Slot()
    def refreshAll(self) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        local_path = self._service.local_path_for(pid)
        remote_path = self._service.remote_path_for(pid)
        self._log.info("remote_files.refresh.requested", "刷新请求", profileId=pid, localPath=local_path, remotePath=remote_path)
        self._run_background(
            lambda: self._service.refresh(pid, local_path, remote_path),
            on_success=lambda _: self._emit_all_active_changed(),
        )

    @Slot(str)
    def changeLocalPath(self, path: str) -> None:
        pid = self._service.active_profile_id()
        self._log.debug("remote_files.local.change_path_requested", "切换本地目录请求", profileId=pid, localPath=path)
        self._run_background(
            lambda: self._service.change_local_path(pid, path),
            on_success=lambda _: (self.localPathChanged.emit(), self.localItemsChanged.emit()),
        )

    @Slot(str)
    def changeRemotePath(self, path: str) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        self._log.info("remote_files.remote.change_path_requested", "切换远程目录请求", profileId=pid, remotePath=path)
        self._run_background(
            lambda: self._service.change_remote_path(pid, path),
            on_success=lambda _: (self.remotePathChanged.emit(), self.remoteItemsChanged.emit()),
        )

    # ------------------------ slots: transfers -------------------------

    @Slot("QVariantList")
    def uploadFiles(self, localPaths) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        paths = [str(item) for item in (localPaths or [])]
        remote_dir = self._service.remote_path_for(pid)
        self._log.info("remote_files.upload.requested", "上传文件请求", profileId=pid, fileCount=len(paths), remotePath=remote_dir)
        self._run_background(
            lambda: self._service.upload(pid, paths, remote_dir),
            on_success=lambda _: self._note(pid, "已加入上传队列"),
        )

    @Slot("QVariantList")
    def uploadPaths(self, localPaths) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        cleaned = [self._normalize_drop_path(item) for item in (localPaths or [])]
        cleaned = [path for path in cleaned if path]
        remote_dir = self._service.remote_path_for(pid)
        self._log.info(
            "remote_files.upload_paths.requested",
            "拖拽上传请求",
            profileId=pid,
            pathCount=len(cleaned),
            remotePath=remote_dir,
        )
        if not cleaned:
            return
        self._run_background(
            lambda: self._service.upload_paths(pid, cleaned, remote_dir),
            on_success=lambda ids: self._note(
                pid,
                f"已加入上传队列 ({len(ids)} 个文件)" if ids else "未发现可上传的文件",
            ),
        )

    @staticmethod
    def _normalize_drop_path(value) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        if text.startswith("file://"):
            import os
            from urllib.parse import unquote, urlparse

            parsed = urlparse(text)
            text = unquote(parsed.path or "")
            if os.name == "nt" and text.startswith("/") and len(text) > 2 and text[2] == ":":
                text = text[1:]
        return text

    @Slot("QVariantList")
    def downloadFiles(self, remoteItems) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        items = [dict(item) for item in (remoteItems or [])]
        local_path = self._service.local_path_for(pid)
        self._log.info("remote_files.download.requested", "下载文件请求", profileId=pid, itemCount=len(items), localPath=local_path)
        self._run_background(
            lambda: self._service.download(pid, items, local_path),
            on_success=lambda _: self._note(pid, "已加入下载队列"),
        )

    @Slot("QVariantList", str)
    def downloadFilesTo(self, remoteItems, targetDir) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        items = [dict(item) for item in (remoteItems or [])]
        target = self._normalize_drop_path(targetDir)
        self._log.info(
            "remote_files.download_to.requested",
            "下载到指定目录请求",
            profileId=pid,
            itemCount=len(items),
            targetDir=target,
        )
        if not items or not target:
            return
        self._run_background(
            lambda: self._service.download_to(pid, items, target),
            on_success=lambda _: self._note(pid, f"已加入下载队列 → {target}"),
        )

    @Slot("QVariantMap", result=bool)
    def canEditRemoteFile(self, item) -> bool:
        return is_editable_file_item(dict(item or {}))

    @Slot("QVariantMap")
    def editRemoteFile(self, item) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        data = dict(item or {})
        remote_path = str(data.get("path") or "")
        remote_dir = self._service.remote_path_for(pid)
        self._log.info("remote_files.edit.requested", "远程文件编辑请求", profileId=pid, remotePath=remote_path)
        self._run_background(
            lambda: self._service.prepare_file_edit(pid, data),
            on_success=lambda edit: self._open_file_edit_session(pid, edit, remote_dir),
        )

    @Slot(str)
    def uploadEditedFile(self, editId: str) -> None:
        edit_id = str(editId or "")
        session = self._edit_sessions.get(edit_id)
        if session is None:
            return
        if session.get("uploading"):
            return
        session["uploading"] = True
        session["pendingUpload"] = False
        profile_id = str(session.get("profileId") or "")
        local_path = str(session.get("localPath") or "")
        remote_path = str(session.get("remotePath") or "")
        remote_dir = str(session.get("remoteDir") or "")
        self._log.info("remote_files.edit.upload_confirmed", "用户确认回传远程编辑文件", profileId=profile_id, remotePath=remote_path)
        self._run_background(
            lambda: self._service.upload_edited_file(profile_id, local_path, remote_path, remote_dir),
            on_success=lambda _result, edit_id=edit_id, profile_id=profile_id: self._on_file_edit_uploaded(edit_id, profile_id),
        )

    @Slot(str)
    def skipEditedFileUpload(self, editId: str) -> None:
        edit_id = str(editId or "")
        session = self._edit_sessions.get(edit_id)
        if session is None:
            return
        session["pendingUpload"] = False
        self._note(str(session.get("profileId") or ""), "已取消本次回传")

    @Slot()
    def syncRemoteFromTerminal(self) -> None:
        """One-shot: jump remote pane to the active terminal's current directory."""

        pid = self._service.active_profile_id()
        if not pid:
            return
        bridge = self._service.terminal_bridge_for(pid)
        if bridge is None:
            return
        current = bridge.current_working_dir() if hasattr(bridge, "current_working_dir") else ""
        if current:
            self._log.info("remote_files.sync_terminal", "使用缓存的终端目录", profileId=pid, remotePath=current)
            self.changeRemotePath(current)
            return
        self._log.info("remote_files.sync_terminal.probe", "向终端发送 pwd 探测", profileId=pid)
        self._pending_terminal_sync = True
        if hasattr(bridge, "requestWorkingDir"):
            bridge.requestWorkingDir()
        self._note(pid, "正在向终端请求当前目录…")

    def _bind_terminal_bridge_for(self, profile_id: str) -> None:
        bridge = self._service.terminal_bridge_for(profile_id)
        if bridge is None:
            return
        if id(bridge) in self._bound_bridges:
            return
        signal = getattr(bridge, "workingDirChanged", None)
        if signal is not None:
            signal.connect(self._on_terminal_dir_changed)
        self._bound_bridges.add(id(bridge))

    def _on_terminal_dir_changed(self, path: str) -> None:
        text = str(path or "")
        if not text:
            return
        if not self._pending_terminal_sync:
            return
        self._pending_terminal_sync = False
        self.changeRemotePath(text)

    @Slot(str)
    def cancelTransfer(self, transferId: str) -> None:
        pid = self._service.active_profile_id()
        self._log.info("remote_files.transfer.cancel_requested", "取消传输请求", profileId=pid, transferId=transferId)
        self._service.cancel_transfer(pid, transferId)

    @Slot()
    def clearFinishedTransfers(self) -> None:
        pid = self._service.active_profile_id()
        self._log.info("remote_files.transfer.clear_finished", "清理已完成传输", profileId=pid)
        self._service.clear_finished_transfers(pid)

    @Slot(str)
    def mkdirRemote(self, name: str) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        clean = str(name or "").strip().strip("/")
        if not clean:
            return
        remote_path = self._service.remote_path_for(pid)
        target = remote_path.rstrip("/") + "/" + clean if remote_path != "/" else "/" + clean
        self._log.info("remote_files.remote.mkdir_requested", "创建远程目录请求", profileId=pid, remotePath=target)
        self._run_background(
            lambda: self._service.mkdir_remote(pid, target),
            on_success=lambda _: self.changeRemotePath(remote_path),
        )

    @Slot(str, str)
    def renameRemote(self, path: str, name: str) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        self._log.info("remote_files.remote.rename_requested", "重命名远程项目请求", profileId=pid, remotePath=path, newName=name)
        remote_path = self._service.remote_path_for(pid)
        self._run_background(
            lambda: self._service.rename_remote(pid, path, name),
            on_success=lambda _: self.changeRemotePath(remote_path),
        )

    @Slot("QVariantList")
    def deleteRemote(self, items) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        data = [dict(item) for item in (items or [])]
        remote_path = self._service.remote_path_for(pid)
        self._log.info("remote_files.remote.delete_requested", "删除远程项目请求", profileId=pid, itemCount=len(data))
        self._run_background(
            lambda: self._service.delete_remote(pid, data),
            on_success=lambda _: self.changeRemotePath(remote_path),
        )

    # ------------------------ slots: terminal --------------------------

    @Slot()
    def openTerminal(self) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        self._log.info("remote_files.terminal.open_requested", "打开 SSH 终端请求", profileId=pid)
        self._run_background(
            lambda: self._service.open_terminal(pid),
            on_success=lambda _: (self._bind_terminal_bridge_for(pid), self.terminalBridgeChanged.emit(), self._note(pid, "终端已连接")),
        )

    @Slot()
    def closeTerminal(self) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        self._log.info("remote_files.terminal.close_requested", "关闭 SSH 终端请求", profileId=pid)
        self._service.close_terminal(pid)
        self.terminalBridgeChanged.emit()
        self._note(pid, "终端已关闭")

    # ------------------------ slots: ftp log ---------------------------

    @Slot()
    def clearFtpLog(self) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        self._service.clear_ftp_log(pid)
        self.ftpLogChanged.emit()

    @Slot()
    def copyFtpLog(self) -> None:
        pid = self._service.active_profile_id()
        lines = self._service.ftp_log_for(pid) if pid else []
        self._copy_ftp_log_text("\n".join(str(line) for line in lines), "日志已复制")

    @Slot(str)
    def copyFtpLogLine(self, line: str) -> None:
        self._copy_ftp_log_text(str(line or ""), "日志行已复制")

    def _copy_ftp_log_text(self, text: str, success_message: str) -> None:
        if not text:
            self.ftpLogCopied.emit(False, "无可复制日志")
            return
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:
            self.ftpLogCopied.emit(False, "剪贴板不可用")
            return
        clipboard.setText(text)
        self.ftpLogCopied.emit(True, success_message)

    def _open_file_edit_session(self, profile_id: str, edit: dict, remote_dir: str) -> None:
        local_path = str(edit.get("localPath") or "")
        remote_path = str(edit.get("remotePath") or "")
        edit_id = str(edit.get("id") or "")
        if not local_path or not remote_path or not edit_id:
            self._note(profile_id, "编辑临时文件准备失败")
            return
        local = Path(local_path)
        try:
            stat_result = local.stat()
        except OSError as exc:
            self._note(profile_id, f"编辑临时文件不可用: {exc}")
            return

        self._edit_sessions[edit_id] = {
            "id": edit_id,
            "profileId": profile_id,
            "remotePath": remote_path,
            "remoteDir": remote_dir,
            "localPath": local_path,
            "lastMtimeNs": int(stat_result.st_mtime_ns),
            "lastSize": int(stat_result.st_size),
            "uploading": False,
            "pendingUpload": False,
        }
        self._ensure_edit_polling()
        opened, message = self._open_local_path(local_path)
        if opened:
            self._note(profile_id, "已打开编辑器，保存后会提示回传")
        else:
            self._edit_sessions.pop(edit_id, None)
            self._ensure_edit_polling()
            self._note(profile_id, message or "打开编辑器失败")

    def _open_local_path(self, local_path: str) -> tuple[bool, str]:
        platform = self._platform
        if platform is not None and hasattr(platform, "open_path"):
            try:
                result = platform.open_path(local_path)
            except Exception as exc:
                return False, str(exc)
            ok = bool(getattr(result, "ok", getattr(result, "success", False)))
            message = str(getattr(result, "message", "") or "")
            return ok, message
        ok = QDesktopServices.openUrl(QUrl.fromLocalFile(local_path))
        return bool(ok), "" if ok else "打开编辑器失败"

    def _ensure_edit_polling(self) -> None:
        if self._edit_sessions:
            if not self._edit_poll_timer.isActive():
                self._edit_poll_timer.start()
            return
        if self._edit_poll_timer.isActive():
            self._edit_poll_timer.stop()

    def _check_file_edit_sessions(self) -> None:
        if self._disposed:
            return
        for edit_id, session in list(self._edit_sessions.items()):
            if session.get("uploading") or session.get("pendingUpload"):
                continue
            local_path = str(session.get("localPath") or "")
            try:
                stat_result = Path(local_path).stat()
            except OSError:
                self._edit_sessions.pop(edit_id, None)
                self._ensure_edit_polling()
                continue
            current_mtime = int(stat_result.st_mtime_ns)
            current_size = int(stat_result.st_size)
            if current_mtime == int(session.get("lastMtimeNs") or 0) and current_size == int(session.get("lastSize") or 0):
                continue
            session["lastMtimeNs"] = current_mtime
            session["lastSize"] = current_size
            session["pendingUpload"] = True
            profile_id = str(session.get("profileId") or "")
            remote_path = str(session.get("remotePath") or "")
            self._log.info("remote_files.edit.changed", "检测到远程文件编辑保存", profileId=profile_id, remotePath=remote_path)
            self._note(profile_id, "检测到编辑内容变更，请确认是否回传")
            self.editedFileUploadRequested.emit(
                {
                    "id": edit_id,
                    "profileId": profile_id,
                    "remotePath": remote_path,
                    "remoteName": Path(remote_path).name,
                    "localPath": local_path,
                }
            )

    def _on_file_edit_uploaded(self, edit_id: str, profile_id: str) -> None:
        session = self._edit_sessions.get(edit_id)
        if session is not None:
            session["uploading"] = False
            session["pendingUpload"] = False
        self.sessionsChanged.emit()
        self._note(profile_id, "编辑内容已上传，列表已刷新")
        if profile_id == self._service.active_profile_id():
            self.remotePathChanged.emit()
            self.remoteItemsChanged.emit()

    @Slot(str, result=QObject)
    def terminalBridgeForProfile(self, profileId: str):
        return self._service.terminal_bridge_for(profileId)

    @Slot(str, result="QVariantList")
    def ftpLogForProfile(self, profileId: str):
        return self._service.ftp_log_for(profileId)

    @Slot(str, result="QVariantMap")
    def snapshotForProfile(self, profileId: str):
        return self._service.snapshot_for(profileId)

    # ------------------------ lifecycle / dispatch ---------------------

    def dispose(self) -> None:
        self._log.info("remote_files.viewmodel.dispose", "释放远程文件插件 ViewModel")
        self._disposed = True
        with self._host_key_lock:
            for event, result in self._pending_host_key_prompts.values():
                result[0] = False
                event.set()
            self._pending_host_key_prompts.clear()
        self._runner.shutdown(wait=False)
        self._edit_poll_timer.stop()
        self._edit_sessions.clear()
        self._service.close()

    def _run_background(self, fn, *, on_success=None) -> None:
        self._runner.start(
            fn,
            on_success=lambda result: self._post_ui(lambda: on_success(result) if on_success is not None else None),
            on_error=lambda exc: self._post_ui(lambda: self._handle_error(exc)),
        )

    def _emit_all_active_changed(self) -> None:
        self.connectionStateChanged.emit()
        self.localPathChanged.emit()
        self.remotePathChanged.emit()
        self.localItemsChanged.emit()
        self.remoteItemsChanged.emit()
        self.transfersChanged.emit()
        self.terminalBridgeChanged.emit()
        self.ftpLogChanged.emit()

    def _set_profiles(self, profiles: list[dict]) -> None:
        self._profiles = list(profiles)
        self.profilesChanged.emit()

    def _note(self, profile_id: str, message: str) -> None:
        pid = str(profile_id or "")
        if not pid:
            return
        self._service.note_message(pid, message)
        self.sessionsChanged.emit()
        if pid == self._service.active_profile_id():
            self.statusMessageChanged.emit()

    def _on_transfers(self, profile_id: str, items: list[dict]) -> None:
        self._refresh_remote_when_uploads_finish(profile_id, items)
        self.sessionsChanged.emit()
        if profile_id == self._service.active_profile_id():
            self.transfersChanged.emit()

    def _refresh_remote_when_uploads_finish(self, profile_id: str, items: list[dict]) -> None:
        uploads = [item for item in items if item.get("direction") == "upload" and item.get("id")]
        if not uploads:
            self._upload_refresh_pending.pop(profile_id, None)
            self._upload_refresh_refreshed.pop(profile_id, None)
            return

        pending = self._upload_refresh_pending.setdefault(profile_id, set())
        refreshed = self._upload_refresh_refreshed.setdefault(profile_id, set())
        active_ids = {
            str(item.get("id"))
            for item in uploads
            if item.get("status") in {"queued", "running"}
        }
        completed_ids = {
            str(item.get("id"))
            for item in uploads
            if item.get("status") == "completed"
        }
        terminal_ids = {
            str(item.get("id"))
            for item in uploads
            if item.get("status") in {"completed", "failed", "cancelled"}
        }

        pending.update(active_ids)
        if active_ids:
            return

        new_completed = completed_ids - refreshed
        pending.difference_update(terminal_ids)
        if not new_completed:
            return

        refreshed.update(completed_ids)
        remote_path = self._service.remote_path_for(profile_id)
        if not remote_path:
            return
        self._log.info("remote_files.upload.refresh_remote", "上传完成后刷新远程列表", profileId=profile_id, remotePath=remote_path)
        self._run_background(
            lambda: self._service.change_remote_path(profile_id, remote_path),
            on_success=lambda _: self._on_upload_refresh_complete(profile_id),
        )

    def _on_upload_refresh_complete(self, profile_id: str) -> None:
        self.sessionsChanged.emit()
        self._note(profile_id, "上传完成，列表已刷新")
        if profile_id == self._service.active_profile_id():
            self.remotePathChanged.emit()
            self.remoteItemsChanged.emit()

    def _on_message(self, profile_id: str, message: str) -> None:
        self._note(profile_id, message)

    def _on_ftp_log(self, profile_id: str, _line: str) -> None:
        self.sessionsChanged.emit()
        if profile_id == self._service.active_profile_id():
            self.ftpLogChanged.emit()

    def _on_snapshot_changed(self, _profile_id: str) -> None:
        self.sessionsChanged.emit()
        if _profile_id == self._service.active_profile_id():
            self.connectionStateChanged.emit()
            self.statusMessageChanged.emit()

    def _handle_error(self, exc: BaseException) -> None:
        message = str(exc)
        pid = self._service.active_profile_id()
        self._clear_failed_edit_uploads()
        self._log.error(
            "remote_files.operation.failed",
            "远程文件操作失败",
            error=message,
            activeProfileId=pid,
        )
        if pid:
            self._note(pid, message)

    def _clear_failed_edit_uploads(self) -> None:
        for session in self._edit_sessions.values():
            session["uploading"] = False

    def _post_ui(self, fn) -> None:
        self._uiCallback.emit(fn)

    @Slot(object)
    def _run_ui_callback(self, fn: object) -> None:
        if not self._disposed and callable(fn):
            fn()
