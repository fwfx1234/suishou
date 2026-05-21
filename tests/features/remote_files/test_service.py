from __future__ import annotations

import os
from pathlib import Path

import pytest
import features.remote_files.service as service_module
from app.platform.models import PlatformResult
from PySide6.QtWidgets import QApplication

from app.storage import StorageManager
from features.remote_files.models import RemoteFileItem
from features.remote_files.service import RemoteFilesService
from features.remote_files.view_model import RemoteFilesViewModel


@pytest.fixture
def qt_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class ListingBackend:
    def __init__(self, *, fail_list: bool = False) -> None:
        self.fail_list = fail_list
        self.listed_paths = []
        self.connected = False
        self.deleted_files = []
        self.deleted_dirs = []

    def connect(self) -> None:
        self.connected = True

    def close(self) -> None:
        self.connected = False

    def list_dir(self, path: str):
        self.listed_paths.append(path)
        if self.fail_list:
            raise RuntimeError("permission denied")
        return [RemoteFileItem("a.txt", f"{path.rstrip('/')}/a.txt", False, 3, 0, "")]

    def delete_file(self, path: str) -> None:
        self.deleted_files.append(path)

    def delete_dir(self, path: str) -> None:
        self.deleted_dirs.append(path)


def test_connect_keeps_connected_when_initial_remote_listing_fails(tmp_path: Path, monkeypatch) -> None:
    database = StorageManager(tmp_path).database("remote_files.db")
    service = RemoteFilesService(database, on_transfers_updated=lambda items: None, on_message=lambda message: None)
    profile = service.profiles.save_profile(
        {
            "name": "prod",
            "protocol": "sftp",
            "host": "example.com",
            "username": "alice",
            "password": "secret",
            "remoteRoot": "/not-readable",
            "localRoot": str(tmp_path),
        }
    )
    backend = ListingBackend(fail_list=True)
    monkeypatch.setattr(service_module, "create_backend", lambda *args, **kwargs: backend)

    result = service.connect(profile.id)
    snapshot = service.snapshot_for(profile.id)

    assert snapshot["status"] == "connected"
    assert "远程目录读取失败" in snapshot["message"]
    assert result.remote_items == []
    assert result.remote_path == "/not-readable"
    assert result.local_items is not None
    assert backend.listed_paths == ["/not-readable"]


class TreeBackend(ListingBackend):
    def list_dir(self, path: str):
        self.listed_paths.append(path)
        if path == "/dir":
            return [
                RemoteFileItem("child.txt", "/dir/child.txt", False, 3, 0, ""),
                RemoteFileItem("nested", "/dir/nested", True, 0, 0, ""),
            ]
        if path == "/dir/nested":
            return [RemoteFileItem("deep.txt", "/dir/nested/deep.txt", False, 4, 0, "")]
        return []


def test_delete_remote_removes_non_empty_directory_recursively(tmp_path: Path, monkeypatch) -> None:
    database = StorageManager(tmp_path).database("remote_files.db")
    service = RemoteFilesService(database, on_transfers_updated=lambda items: None, on_message=lambda message: None)
    profile = service.profiles.save_profile(
        {
            "name": "prod",
            "protocol": "sftp",
            "host": "example.com",
            "username": "alice",
            "password": "secret",
        }
    )
    backend = TreeBackend()
    monkeypatch.setattr(service_module, "create_backend", lambda *args, **kwargs: backend)
    service.connect(profile.id)

    service.delete_remote(profile.id, [{"path": "/dir", "isDir": True}])

    assert backend.listed_paths[-2:] == ["/dir", "/dir/nested"]
    assert backend.deleted_files == ["/dir/child.txt", "/dir/nested/deep.txt"]
    assert backend.deleted_dirs == ["/dir/nested", "/dir"]


class EditableBackend(ListingBackend):
    def __init__(self) -> None:
        super().__init__()
        self.files = {"/docs/a.txt": b"hello"}
        self.uploaded = []

    def list_dir(self, path: str):
        self.listed_paths.append(path)
        if path == "/docs":
            data = self.files["/docs/a.txt"]
            return [RemoteFileItem("a.txt", "/docs/a.txt", False, len(data), 0, "")]
        return []

    def download_file(self, remote_path: str, local_path: str, progress=None) -> None:
        del progress
        Path(local_path).write_bytes(self.files[remote_path])

    def upload_file(self, local_path: str, remote_path: str, progress=None) -> None:
        del progress
        data = Path(local_path).read_bytes()
        self.files[remote_path] = data
        self.uploaded.append((remote_path, data))


def test_prepare_file_edit_downloads_then_uploads_and_refreshes(tmp_path: Path, monkeypatch) -> None:
    database = StorageManager(tmp_path).database("remote_files.db")
    service = RemoteFilesService(
        database,
        on_transfers_updated=lambda items: None,
        on_message=lambda message: None,
        edit_root=tmp_path / "edits",
    )
    profile = service.profiles.save_profile(
        {
            "name": "prod",
            "protocol": "sftp",
            "host": "example.com",
            "username": "alice",
            "password": "secret",
            "remoteRoot": "/docs",
        }
    )
    backend = EditableBackend()
    monkeypatch.setattr(service_module, "create_backend", lambda *args, **kwargs: backend)
    service.connect(profile.id)

    edit = service.prepare_file_edit(
        profile.id,
        {"name": "a.txt", "path": "/docs/a.txt", "isDir": False, "size": 5},
    )
    local_path = Path(edit["localPath"])
    local_path.write_text("updated", encoding="utf-8")
    result = service.upload_edited_file(profile.id, str(local_path), "/docs/a.txt", "/docs")

    assert backend.uploaded == [("/docs/a.txt", b"updated")]
    assert backend.listed_paths[-1] == "/docs"
    assert result.remote_path == "/docs"
    remote_file = next(item for item in service.remote_items_for(profile.id) if item["name"] == "a.txt")
    assert remote_file["size"] == len(b"updated")


def test_file_edit_accepts_any_file_and_rejects_directories(tmp_path: Path) -> None:
    database = StorageManager(tmp_path).database("remote_files.db")
    service = RemoteFilesService(database, on_transfers_updated=lambda items: None, on_message=lambda message: None)

    assert service.can_edit_file_item({"name": "notes.md", "path": "/notes.md", "isDir": False, "size": 10})
    assert service.can_edit_file_item({"name": "big.zip", "path": "/big.zip", "isDir": False, "size": 60 * 1024 * 1024})
    assert service.can_edit_file_item({"name": "photo.png", "path": "/photo.png", "isDir": False, "size": 10})
    assert not service.can_edit_file_item({"name": "notes.md", "path": "/notes.md", "isDir": True, "size": 10})


class RefreshService:
    def __init__(self) -> None:
        self.refreshed = []
        self.notes = []
        self.log_lines = []

    def active_profile_id(self):
        return "p1"

    def remote_path_for(self, profile_id):
        return "/upload-target" if profile_id == "p1" else ""

    def change_remote_path(self, profile_id, remote_path):
        self.refreshed.append((profile_id, remote_path))

    def ftp_log_for(self, profile_id):
        return list(self.log_lines)

    def note_message(self, profile_id, message):
        self.notes.append((profile_id, message))

    def close(self):
        pass


def test_view_model_refreshes_remote_listing_after_upload_batch_finishes(tmp_path: Path, qt_app) -> None:
    database = StorageManager(tmp_path).database("remote_files.db")
    vm = RemoteFilesViewModel(database)
    fake = RefreshService()
    vm._service = fake
    vm._run_background = lambda fn, on_success=None: (fn(), on_success(None) if on_success is not None else None)
    changed = []
    vm.remoteItemsChanged.connect(lambda: changed.append(True))

    vm._on_transfers(
        "p1",
        [{"id": "u1", "direction": "upload", "status": "running"}],
    )
    vm._on_transfers(
        "p1",
        [{"id": "u1", "direction": "upload", "status": "completed"}],
    )
    qt_app.processEvents()
    vm.dispose()

    assert fake.refreshed == [("p1", "/upload-target")]
    assert fake.notes[-1] == ("p1", "上传完成，列表已刷新")
    assert changed


def test_view_model_copies_ftp_log_to_clipboard(tmp_path: Path, qt_app) -> None:
    database = StorageManager(tmp_path).database("remote_files.db")
    vm = RemoteFilesViewModel(database)
    fake = RefreshService()
    fake.log_lines = ["> LIST /remote", "< LIST 2 lines"]
    vm._service = fake
    copied = []
    vm.ftpLogCopied.connect(lambda ok, message: copied.append((ok, message)))

    vm.copyFtpLog()
    qt_app.processEvents()
    vm.dispose()

    assert copied == [(True, "日志已复制")]
    assert qt_app.clipboard().text() == "> LIST /remote\n< LIST 2 lines"


class FileEditService(RefreshService):
    def __init__(self, local_path: Path) -> None:
        super().__init__()
        self.local_path = local_path
        self.uploads = []

    def prepare_file_edit(self, profile_id, item):
        self.local_path.write_text("hello", encoding="utf-8")
        return {
            "id": "edit-1",
            "profileId": profile_id,
            "remotePath": item["path"],
            "remoteName": item["name"],
            "localPath": str(self.local_path),
        }

    def upload_edited_file(self, profile_id, local_path, remote_path, refresh_remote_path):
        self.uploads.append((profile_id, Path(local_path).read_text(encoding="utf-8"), remote_path, refresh_remote_path))


class FileEditPlatform:
    def __init__(self) -> None:
        self.opened = []

    def open_path(self, path: str) -> PlatformResult:
        self.opened.append(path)
        return PlatformResult(True)


def test_view_model_prompts_then_uploads_edited_file_after_confirmation(tmp_path: Path, qt_app) -> None:
    database = StorageManager(tmp_path).database("remote_files.db")
    platform = FileEditPlatform()
    vm = RemoteFilesViewModel(database, platform_api=platform)
    local_path = tmp_path / "edit.txt"
    fake = FileEditService(local_path)
    vm._service = fake

    def run_now(fn, on_success=None):
        result = fn()
        if on_success is not None:
            on_success(result)

    vm._run_background = run_now
    prompts = []
    vm.editedFileUploadRequested.connect(lambda info: prompts.append(dict(info)))
    vm.editRemoteFile({"name": "a.txt", "path": "/remote/a.txt", "isDir": False, "size": 5})
    local_path.write_text("changed", encoding="utf-8")
    os.utime(local_path, None)
    vm._check_file_edit_sessions()
    assert fake.uploads == []
    assert prompts and prompts[0]["remotePath"] == "/remote/a.txt"
    vm.uploadEditedFile(prompts[0]["id"])
    qt_app.processEvents()
    vm.dispose()

    assert platform.opened == [str(local_path)]
    assert fake.uploads == [("p1", "changed", "/remote/a.txt", "/upload-target")]
