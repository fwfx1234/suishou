from __future__ import annotations

from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from .executor import QuickLaunchExecutor
from .registrar import QuickLaunchRegistrar
from .repository import QuickLaunchRepository


def _log():
    from app.logging import get_logger

    return get_logger("features.quick_launch.view_model")


class QuickLaunchViewModel(QObject):
    actionsChanged = Signal()
    runsChanged = Signal()
    pendingActionChanged = Signal()
    pendingParametersChanged = Signal()
    initialModeChanged = Signal()
    feedbackMessageChanged = Signal()
    popupResult = Signal("QVariantMap")
    searchQueryChanged = Signal()
    runningChanged = Signal()
    _backgroundRunFinished = Signal(int, str, object)

    def __init__(
        self,
        repository: QuickLaunchRepository,
        executor: QuickLaunchExecutor,
        registrar: QuickLaunchRegistrar,
        *,
        initial_action_id: int = 0,
        initial_mode: str = "manage",
        platform: object | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._repository = repository
        self._executor = executor
        self._registrar = registrar
        self._platform = platform
        self._actions: list[dict] = []
        self._runs: list[dict] = []
        self._search_query = ""
        self._pending_action_id: int = 0
        self._pending_parameters: list[dict] = []
        self._initial_mode = initial_mode
        self._feedback_message: str = ""
        self._running_action_ids: list[int] = []
        self._backgroundRunFinished.connect(self._on_background_run_finished)
        self._reload_actions()
        self._reload_runs()
        if initial_action_id > 0 and initial_mode == "form":
            self._open_pending(initial_action_id)

    # ----- properties -----

    @Property("QVariantList", notify=actionsChanged)
    def actions(self) -> list[dict]:
        return list(self._actions)

    @Property("QVariantList", notify=runsChanged)
    def runs(self) -> list[dict]:
        return list(self._runs)

    @Property(str, notify=searchQueryChanged)
    def searchQuery(self) -> str:
        return self._search_query

    @Property(int, notify=pendingActionChanged)
    def pendingActionId(self) -> int:
        return self._pending_action_id

    @Property("QVariantList", notify=pendingParametersChanged)
    def pendingParameters(self) -> list[dict]:
        return list(self._pending_parameters)

    @Property(str, notify=initialModeChanged)
    def initialMode(self) -> str:
        return self._initial_mode

    @Property(str, notify=feedbackMessageChanged)
    def feedbackMessage(self) -> str:
        return self._feedback_message

    @Property("QVariantList", notify=runningChanged)
    def runningActionIds(self) -> list[int]:
        return list(self._running_action_ids)

    # ----- search -----

    @Slot(str)
    def setSearchQuery(self, text: str) -> None:
        normalized = (text or "").strip()
        if normalized == self._search_query:
            return
        self._search_query = normalized
        self.searchQueryChanged.emit()
        self._reload_actions()

    # ----- action CRUD -----

    @Slot("QVariantMap", result=int)
    def createAction(self, payload: dict) -> int:
        params = self._normalize_action_payload(payload)
        if not params["name"]:
            self._set_feedback("动作名称不能为空")
            return 0
        action = self._repository.create_action(**params)
        self._reload_actions()
        self._registrar.sync_action(action.id)
        self._set_feedback(f"已创建动作 {action.name}")
        return action.id

    @Slot(int, "QVariantMap", result=bool)
    def updateAction(self, action_id: int, payload: dict) -> bool:
        if action_id <= 0:
            return False
        params = self._normalize_action_payload(payload)
        updated = self._repository.update_action(int(action_id), **params)
        if updated is None:
            return False
        self._reload_actions()
        self._registrar.sync_action(int(action_id))
        self._set_feedback(f"已保存动作 {updated.name}")
        return True

    @Slot(int, result=bool)
    def deleteAction(self, action_id: int) -> bool:
        if action_id <= 0:
            return False
        self._executor.stop(int(action_id))
        ok = self._repository.delete_action(int(action_id))
        if not ok:
            return False
        self._registrar.sync_action(int(action_id))
        self._reload_actions()
        self._set_feedback("已删除动作")
        return True

    @Slot(int, bool, result=bool)
    def setActionEnabled(self, action_id: int, enabled: bool) -> bool:
        if action_id <= 0:
            return False
        if not enabled:
            self._executor.stop(int(action_id))
        updated = self._repository.set_action_enabled(int(action_id), bool(enabled))
        if updated is None:
            return False
        self._reload_actions()
        self._registrar.sync_action(int(action_id))
        self._set_feedback("已启用" if enabled else "已停用")
        return True

    @Slot(int, result=bool)
    def stopAction(self, action_id: int) -> bool:
        if action_id <= 0:
            return False
        stopped = self._executor.stop(int(action_id))
        if stopped:
            self._set_feedback("已请求停止")
        return bool(stopped)

    @Slot(int, result=bool)
    def isActionRunning(self, action_id: int) -> bool:
        if action_id <= 0:
            return False
        return self._executor.is_running(int(action_id))

    @Slot(int, result=bool)
    def duplicateAction(self, action_id: int) -> bool:
        existing = self._repository.get_action(int(action_id))
        if existing is None:
            return False
        cloned = self._repository.create_action(
            name=f"{existing.name} 副本",
            description=existing.description,
            kind=existing.kind,
            script_type=existing.script_type,
            script_source=existing.script_source,
            script_body=existing.script_body,
            interpreter=existing.interpreter,
            path=existing.path,
            url=existing.url,
            args=existing.args,
            cwd=existing.cwd,
            env=existing.env,
            keywords=existing.keywords,
            prefixes=existing.prefixes,
            icon=existing.icon,
            feedback_mode=existing.feedback_mode,
            timeout_sec=existing.timeout_sec,
            enabled=existing.enabled,
        )
        self._reload_actions()
        self._registrar.sync_action(cloned.id)
        self._set_feedback(f"已复制为 {cloned.name}")
        return True

    @Slot(int, result="QVariantMap")
    def actionDetail(self, action_id: int) -> dict:
        action = self._repository.get_action(int(action_id))
        return action.to_dict() if action else {}

    @Slot(int, result="QVariantList")
    def parametersOf(self, action_id: int) -> list[dict]:
        action = self._repository.get_action(int(action_id))
        if action is None:
            return []
        names = self._executor.required_parameters(action)
        return [{"name": name, "value": ""} for name in names]

    # ----- execution -----

    @Slot(int, result="QVariantMap")
    def runNow(self, action_id: int) -> dict:
        action = self._repository.get_action(int(action_id))
        if action is None:
            return {"ok": False, "status": "error", "message": "动作不存在"}
        if self._executor.is_running(int(action_id)):
            message = "动作正在执行，请稍候"
            self._set_feedback(message)
            return {"ok": False, "status": "running", "message": message}
        params = self._executor.required_parameters(action)
        if params:
            self._open_pending(action_id)
            return {
                "ok": False,
                "status": "needsParameters",
                "message": "请填写参数后再执行",
                "parameters": [{"name": name, "value": ""} for name in params],
            }
        self._executor.execute_in_background(
            action, on_done=lambda r: self._after_background_run(action.id, action.name, r)
        )
        self._mark_running(action.id)
        message = f"已开始执行 {action.name}"
        self._set_feedback(message)
        return {"ok": True, "status": "started", "message": message}

    @Slot(int, "QVariantMap", result="QVariantMap")
    def runWithParameters(self, action_id: int, parameters: dict) -> dict:
        action = self._repository.get_action(int(action_id))
        if action is None:
            return {"ok": False, "status": "error", "message": "动作不存在"}
        if self._executor.is_running(int(action_id)):
            message = "动作正在执行，请稍候"
            self._set_feedback(message)
            return {"ok": False, "status": "running", "message": message}
        normalized = {str(k): "" if v is None else str(v) for k, v in (parameters or {}).items()}
        missing = self._missing_parameters(action, normalized)
        if missing:
            message = f"缺少参数: {', '.join(missing)}"
            self._set_feedback(message)
            return {
                "ok": False,
                "status": "needsParameters",
                "message": message,
                "missing": list(missing),
            }
        self._executor.execute_in_background(
            action,
            parameters=normalized,
            on_done=lambda r: self._after_background_run(action.id, action.name, r),
        )
        self._mark_running(action.id)
        self._clear_pending()
        message = f"已开始执行 {action.name}"
        self._set_feedback(message)
        return {"ok": True, "status": "started", "message": message}

    @Slot()
    def clearPending(self) -> None:
        self._clear_pending()

    @Slot()
    def refreshRuns(self) -> None:
        self._reload_runs()

    # ----- platform helpers (native file pickers) -----

    @Slot(result=str)
    def pickScriptFile(self) -> str:
        if self._platform is None:
            return ""
        try:
            from app.platform.models import FileDialogFilter, FileDialogOptions

            opts = FileDialogOptions(
                title="选择脚本文件",
                filters=[
                    FileDialogFilter(name="脚本", patterns=["*.sh", "*.zsh", "*.bash", "*.js", "*.mjs", "*.cjs", "*.ts", "*.py", "*"]),
                ],
            )
            path = self._platform.dialogs.open_file(opts)
            return str(path) if path else ""
        except Exception:
            return ""

    @Slot(result=str)
    def pickDirectory(self) -> str:
        if self._platform is None:
            return ""
        try:
            from app.platform.models import FileDialogOptions

            opts = FileDialogOptions(title="选择工作目录")
            path = self._platform.dialogs.open_directory(opts)
            return str(path) if path else ""
        except Exception:
            return ""

    # ----- internals -----

    def _missing_parameters(self, action, values: dict[str, str]) -> list[str]:
        required = self._executor.required_parameters(action)
        return [name for name in required if not values.get(name, "").strip()]

    def _mark_running(self, action_id: int) -> None:
        action_id = int(action_id)
        if action_id in self._running_action_ids:
            return
        self._running_action_ids.append(action_id)
        self.runningChanged.emit()

    def _unmark_running(self, action_id: int) -> None:
        action_id = int(action_id)
        if action_id not in self._running_action_ids:
            return
        self._running_action_ids.remove(action_id)
        self.runningChanged.emit()

    def _after_background_run(self, action_id: int, action_name: str, result) -> None:
        # Called from worker thread - hop back to Qt main thread via signal.
        self._backgroundRunFinished.emit(int(action_id), str(action_name), result)

    @Slot(int, str, object)
    def _on_background_run_finished(self, action_id: int, action_name: str, result) -> None:
        self._unmark_running(action_id)
        self._reload_runs()
        message = result.message or ("执行成功" if result.ok else "执行失败")
        self._set_feedback(message)
        self._maybe_emit_popup(action_id, action_name, result)

    def _maybe_emit_popup(self, action_id: int, action_name: str, result) -> None:
        if result.feedback_mode != "popup":
            return
        run = result.run
        payload = {
            "actionId": action_id,
            "actionName": action_name,
            "status": result.status,
            "ok": result.ok,
            "exitCode": run.exit_code if run else None,
            "durationMs": run.duration_ms if run else 0,
            "stdout": run.stdout if run else "",
            "stderr": run.stderr if run else "",
            "message": result.message,
        }
        self.popupResult.emit(payload)

    def _normalize_action_payload(self, payload: dict) -> dict[str, Any]:
        payload = dict(payload or {})
        keywords = self._coerce_str_list(payload.get("keywords"))
        prefixes = self._coerce_str_list(payload.get("prefixes"))
        env_raw = payload.get("env") or {}
        env: dict[str, str]
        if isinstance(env_raw, dict):
            env = {str(k): "" if v is None else str(v) for k, v in env_raw.items()}
        else:
            env = {}
        feedback_mode = str(payload.get("feedbackMode") or "notification")
        if feedback_mode not in {"silent", "popup", "notification"}:
            feedback_mode = "notification"
        kind = str(payload.get("kind") or "script")
        if kind not in {"script", "open_path", "open_url"}:
            kind = "script"
        script_type = str(payload.get("scriptType") or "shell")
        if script_type not in {"shell", "node", "python", "other"}:
            script_type = "shell"
        script_source = str(payload.get("scriptSource") or "path")
        if script_source not in {"path", "inline"}:
            script_source = "path"
        try:
            timeout_sec = int(payload.get("timeoutSec") or 300)
        except (TypeError, ValueError):
            timeout_sec = 300
        return {
            "name": str(payload.get("name") or "").strip(),
            "description": str(payload.get("description") or ""),
            "kind": kind,
            "script_type": script_type,
            "script_source": script_source,
            "script_body": str(payload.get("scriptBody") or ""),
            "interpreter": str(payload.get("interpreter") or ""),
            "path": str(payload.get("path") or ""),
            "url": str(payload.get("url") or ""),
            "args": str(payload.get("args") or ""),
            "cwd": str(payload.get("cwd") or ""),
            "env": env,
            "keywords": keywords,
            "prefixes": prefixes,
            "icon": str(payload.get("icon") or ""),
            "feedback_mode": feedback_mode,
            "timeout_sec": timeout_sec,
            "enabled": bool(payload.get("enabled", True)),
        }

    @staticmethod
    def _coerce_str_list(value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, (list, tuple)):
            return [str(item).strip() for item in value if str(item).strip()]
        return []

    def _reload_actions(self) -> None:
        items = self._repository.list_actions()
        query = self._search_query.lower()
        if query:
            filtered: list = []
            for item in items:
                haystack = " ".join([
                    item.name,
                    item.description,
                    item.path,
                    item.url,
                    item.args,
                    item.script_body,
                    " ".join(item.keywords or []),
                    " ".join(item.prefixes or []),
                ]).lower()
                if query in haystack:
                    filtered.append(item)
            items = filtered
        self._actions = [action.to_dict() for action in items]
        self.actionsChanged.emit()

    def _reload_runs(self) -> None:
        runs = self._repository.list_runs(limit=50)
        self._runs = [run.to_dict() for run in runs]
        self.runsChanged.emit()

    def _open_pending(self, action_id: int) -> None:
        action = self._repository.get_action(int(action_id))
        if action is None:
            return
        names = self._executor.required_parameters(action)
        self._pending_action_id = action.id
        self._pending_parameters = [{"name": name, "value": ""} for name in names]
        self.pendingActionChanged.emit()
        self.pendingParametersChanged.emit()

    def _clear_pending(self) -> None:
        if self._pending_action_id == 0 and not self._pending_parameters:
            return
        self._pending_action_id = 0
        self._pending_parameters = []
        self.pendingActionChanged.emit()
        self.pendingParametersChanged.emit()

    def _set_feedback(self, message: str) -> None:
        self._feedback_message = message
        self.feedbackMessageChanged.emit()
