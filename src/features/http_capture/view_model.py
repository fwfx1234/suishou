from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal, Slot

from .service import CaptureState, FlowSummary, HttpCaptureService, filter_rows


class HttpCaptureViewModel(QObject):
    captureStateUpdated = Signal("QVariantMap")
    captureRowsUpdated = Signal("QVariantList")
    captureDetailUpdated = Signal("QVariantMap")
    captureStatsUpdated = Signal("QVariantMap")
    captureActionResult = Signal(bool, str)
    _uiCallback = Signal(object)

    def __init__(self, platform_api: object | None = None) -> None:
        super().__init__()
        self._disposed = False
        self._platform = platform_api
        self._uiCallback.connect(self._run_ui_callback)
        self._service = HttpCaptureService(
            on_state_changed=self._on_state_changed,
            on_flow_event=self._on_flow_event,
            data_dir=self._plugin_data_dir(),
        )
        self._capture_busy = False
        self._capture_busy_text = ""
        self._capture_busy_lock = threading.Lock()
        self._filter_keyword = ""
        self._filter_host = ""
        self._filter_method = ""
        self._filter_content_type = ""
        self._filter_scheme = ""
        self._filter_status_min = 0
        self._filter_status_max = 0
        self._filter_only_errors = False
        self._filter_hide_static = False
        self._filter_min_duration_ms = 0
        self._last_filtered_ids: list[str] = []
        self._emit_state(self._service.state)
        self._publish_rows()

    @Slot(result="QVariantMap")
    def initialState(self) -> dict:
        if self._service is None:
            return {}
        return self._service.state.to_dict()

    @Slot()
    def startHttpCapture(self) -> None:
        if self._service is None:
            return
        self._start_capture(mobile=False)

    @Slot()
    def startMobileCapture(self) -> None:
        if self._service is None:
            return
        self._start_capture(mobile=True)

    def _start_capture(self, *, mobile: bool) -> None:
        if self._service is None:
            return
        if not self._begin_capture_busy("正在启动手机抓包..." if mobile else "正在启动代理..."):
            self.captureActionResult.emit(False, "代理正在启动或停止")
            return

        def runner() -> None:
            service = self._service
            if service is None:
                self._end_capture_busy()
                return
            state = service.start_mobile() if mobile else service.start()
            ok = state.running and not state.error
            if ok:
                if state.system_proxy_enabled:
                    message = f"代理运行中，系统代理已接管: {state.proxy_url}"
                elif state.system_proxy_error:
                    message = f"代理运行中，但{state.system_proxy_error}；请手动设置代理 {state.proxy_url}"
                else:
                    message = f"代理运行中: {state.proxy_url}"
                if mobile and state.mobile_proxy_url:
                    message = f"手机抓包已启动: {state.mobile_proxy_url}"
            else:
                message = state.error or "代理启动失败"
            self._end_capture_busy()
            self._post_ui(lambda success=ok, text=message: self.captureActionResult.emit(success, text))

        threading.Thread(target=runner, name="http-capture-start", daemon=True).start()

    @Slot()
    def stopHttpCapture(self) -> None:
        if self._service is None:
            return
        if not self._begin_capture_busy("正在停止代理..."):
            self.captureActionResult.emit(False, "代理正在启动或停止")
            return

        def runner() -> None:
            service = self._service
            if service is None:
                self._end_capture_busy()
                return
            state = service.stop()
            self._end_capture_busy()
            self._post_ui(lambda: self.captureActionResult.emit(not state.running, "代理已停止" if not state.running else "代理停止超时"))

        threading.Thread(target=runner, name="http-capture-stop", daemon=True).start()

    @Slot()
    def pauseHttpCapture(self) -> None:
        if self._service is None:
            return
        self._service.pause()

    @Slot()
    def resumeHttpCapture(self) -> None:
        if self._service is None:
            return
        self._service.resume()

    @Slot()
    def clearCaptureRows(self) -> None:
        if self._service is None:
            return
        self._service.clear()
        self.captureDetailUpdated.emit({})
        self._publish_rows()

    @Slot(str)
    def selectFlow(self, flowId: str) -> None:
        if self._service is None:
            self.captureDetailUpdated.emit({})
            return
        detail = self._service.detail(flowId)
        if detail is None:
            self.captureDetailUpdated.emit({})
        else:
            self.captureDetailUpdated.emit(detail.to_dict())

    @Slot(str)
    def copyCurl(self, flowId: str) -> None:
        if self._service is None:
            self.captureActionResult.emit(False, "HTTP 抓包服务不可用")
            return
        text = self._service.build_curl(flowId)
        if not text:
            self.captureActionResult.emit(False, "无可复制内容")
            return
        ok = self._write_clipboard(text)
        self.captureActionResult.emit(ok, "已复制 cURL" if ok else "复制失败")

    @Slot(str)
    def copyUrl(self, flowId: str) -> None:
        if self._service is None:
            self.captureActionResult.emit(False, "HTTP 抓包服务不可用")
            return
        text = self._service.request_url(flowId)
        if not text:
            self.captureActionResult.emit(False, "无可复制 URL")
            return
        ok = self._write_clipboard(text)
        self.captureActionResult.emit(ok, "已复制 URL" if ok else "复制失败")

    @Slot()
    def revealCertDir(self) -> None:
        if self._service is None:
            self.captureActionResult.emit(False, "HTTP 抓包服务不可用")
            return
        target = self._service.cert_directory()
        try:
            target.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            self.captureActionResult.emit(False, f"无法访问目录: {exc}")
            return
        if self._platform is None:
            self.captureActionResult.emit(False, "平台 API 不可用")
            return
        result = self._platform.open_path(target)
        self.captureActionResult.emit(
            bool(getattr(result, "success", False)),
            getattr(result, "message", "") or str(target),
        )

    @Slot()
    def openCertInstallUrl(self) -> None:
        if self._service is None:
            self.captureActionResult.emit(False, "HTTP 抓包服务不可用")
            return
        if self._platform is None:
            self.captureActionResult.emit(False, "平台 API 不可用")
            return
        result = self._platform.open_url(self._service.cert_install_url())
        self.captureActionResult.emit(
            bool(getattr(result, "success", False)),
            getattr(result, "message", "") or self._service.cert_install_url(),
        )

    @Slot()
    def installDesktopCertificate(self) -> None:
        if self._service is None:
            self.captureActionResult.emit(False, "HTTP 抓包服务不可用")
            return

        def runner() -> None:
            service = self._service
            if service is None:
                return
            ok, message = service.install_desktop_certificate()
            self._emit_state(service.state)
            self._post_ui(lambda success=ok, text=message: self.captureActionResult.emit(success, text))

        threading.Thread(target=runner, name="http-capture-cert-install", daemon=True).start()

    @Slot()
    def copyProxyAddress(self) -> None:
        if self._service is None:
            self.captureActionResult.emit(False, "HTTP 抓包服务不可用")
            return
        state = self._service.state
        if not state.proxy_url:
            self.captureActionResult.emit(False, "代理未启动")
            return
        ok = self._write_clipboard(state.proxy_url)
        self.captureActionResult.emit(ok, state.proxy_url if ok else "复制失败")

    @Slot()
    def copyMobileProxyAddress(self) -> None:
        if self._service is None:
            self.captureActionResult.emit(False, "HTTP 抓包服务不可用")
            return
        state = self._service.state
        if not state.mobile_proxy_url:
            self.captureActionResult.emit(False, "手机抓包未启动或未识别到局域网 IP")
            return
        ok = self._write_clipboard(state.mobile_proxy_url)
        self.captureActionResult.emit(ok, state.mobile_proxy_url if ok else "复制失败")

    @Slot()
    def copyCertInstallUrl(self) -> None:
        if self._service is None:
            self.captureActionResult.emit(False, "HTTP 抓包服务不可用")
            return
        text = self._service.cert_install_url()
        ok = self._write_clipboard(text)
        self.captureActionResult.emit(ok, text if ok else "复制失败")

    @Slot()
    def recoverSystemProxy(self) -> None:
        if self._service is None:
            return
        if not self._begin_capture_busy("正在恢复系统代理..."):
            self.captureActionResult.emit(False, "代理正在启动或停止")
            return

        def runner() -> None:
            service = self._service
            if service is None:
                self._end_capture_busy()
                return
            state = service.recover_system_proxy_if_needed()
            ok = not state.system_proxy_error
            message = state.system_proxy_recovery_message or ("系统代理已恢复" if ok else state.system_proxy_error)
            self._end_capture_busy()
            self._post_ui(lambda success=ok, text=message: self.captureActionResult.emit(success, text))

        threading.Thread(target=runner, name="http-capture-proxy-recover", daemon=True).start()

    @Slot(str, str)
    def saveResponseBody(self, flowId: str, savePath: str) -> None:
        if not savePath:
            self.captureActionResult.emit(False, "未提供保存路径")
            return
        if self._service is None:
            self.captureActionResult.emit(False, "HTTP 抓包服务不可用")
            return
        target = _path_from_qml(savePath)
        ok, message = self._service.save_response_body(flowId, target)
        self.captureActionResult.emit(ok, message)

    @Slot(str)
    def replayFlow(self, flowId: str) -> None:
        if not flowId:
            self.captureActionResult.emit(False, "请选择一条会话")
            return

        def runner() -> None:
            service = self._service
            if service is None:
                return
            ok, message, summary = service.replay_flow(flowId)
            detail = service.detail(summary.id) if summary is not None else None
            self._publish_rows()
            self._post_ui(lambda success=ok, text=message: self.captureActionResult.emit(success, text))
            if detail is not None:
                self._post_ui(lambda data=detail.to_dict(): self.captureDetailUpdated.emit(data))

        threading.Thread(target=runner, name="http-capture-replay", daemon=True).start()

    @Slot(str, str, str, str)
    def sendComposerRequest(self, method: str, url: str, headersText: str, bodyText: str) -> None:
        if not url.strip():
            self.captureActionResult.emit(False, "请输入请求 URL")
            return

        def runner() -> None:
            service = self._service
            if service is None:
                return
            ok, message, summary = service.send_composer_request(method, url, headersText, bodyText)
            detail = service.detail(summary.id) if summary is not None else None
            self._publish_rows()
            self._post_ui(lambda success=ok, text=message: self.captureActionResult.emit(success, text))
            if detail is not None:
                self._post_ui(lambda data=detail.to_dict(): self.captureDetailUpdated.emit(data))

        threading.Thread(target=runner, name="http-capture-composer", daemon=True).start()

    @Slot(str, str)
    def exportSelectedSession(self, flowId: str, savePath: str) -> None:
        self._export_sessions([flowId] if flowId else [], savePath, _format_from_path(savePath))

    @Slot(str, str)
    def exportVisibleSessions(self, savePath: str, exportFormat: str) -> None:
        self._export_sessions(list(self._last_filtered_ids), savePath, exportFormat)

    @Slot(str, str, str, str, int, int, str, bool, bool, int)
    def setFilters(
        self,
        keyword: str,
        host: str,
        method: str,
        contentType: str,
        statusMin: int,
        statusMax: int,
        scheme: str,
        onlyErrors: bool,
        hideStatic: bool,
        minDurationMs: int,
    ) -> None:
        self._filter_keyword = keyword or ""
        self._filter_host = host or ""
        self._filter_method = method or ""
        self._filter_content_type = contentType or ""
        self._filter_status_min = int(statusMin or 0)
        self._filter_status_max = int(statusMax or 0)
        self._filter_scheme = scheme or ""
        self._filter_only_errors = bool(onlyErrors)
        self._filter_hide_static = bool(hideStatic)
        self._filter_min_duration_ms = int(minDurationMs or 0)
        self._publish_rows()

    def dispose(self) -> None:
        self._disposed = True
        try:
            self._service.stop()
        except Exception:
            pass
        try:
            self._uiCallback.disconnect(self._run_ui_callback)
        except (RuntimeError, TypeError):
            pass
        self._service = None
        self._platform = None

    def _publish_rows(self) -> None:
        if self._service is None:
            return
        rows = self._service.rows()
        filtered = filter_rows(
            rows,
            keyword=self._filter_keyword,
            host=self._filter_host,
            method=self._filter_method,
            status_min=self._filter_status_min,
            status_max=self._filter_status_max,
            content_type=self._filter_content_type,
            scheme=self._filter_scheme,
            only_errors=self._filter_only_errors,
            hide_static=self._filter_hide_static,
            min_duration_ms=self._filter_min_duration_ms,
        )
        self._last_filtered_ids = [row.id for row in filtered]
        payload = [row.to_dict() for row in filtered]
        stats = self._service.stats(filtered)
        self._post_ui(lambda data=payload: self._emit_rows_in_ui(data))
        self._post_ui(lambda data=stats: self._emit_stats_in_ui(data))

    def _on_state_changed(self, state: CaptureState) -> None:
        if self._disposed:
            return
        self._emit_state(state)

    def _on_flow_event(self, kind: str, summary: FlowSummary) -> None:
        if self._disposed:
            return
        del kind, summary
        self._publish_rows()

    def _emit_state(self, state: CaptureState) -> None:
        snapshot = self._state_payload(state)
        self._post_ui(lambda data=snapshot: self._emit_state_in_ui(data))

    def _state_payload(self, state: CaptureState) -> dict:
        payload = state.to_dict()
        with self._capture_busy_lock:
            payload["busy"] = self._capture_busy
            payload["busyText"] = self._capture_busy_text
        return payload

    def _begin_capture_busy(self, message: str) -> bool:
        with self._capture_busy_lock:
            if self._capture_busy:
                return False
            self._capture_busy = True
            self._capture_busy_text = message
        service = self._service
        if service is not None:
            self._emit_state(service.state)
        self._post_ui(lambda text=message: self.captureActionResult.emit(True, text))
        return True

    def _end_capture_busy(self) -> None:
        with self._capture_busy_lock:
            self._capture_busy = False
            self._capture_busy_text = ""
        service = self._service
        if service is not None:
            self._emit_state(service.state)

    def _write_clipboard(self, text: str) -> bool:
        if self._platform is None:
            return False
        try:
            result = self._platform.clipboard.write_text(text)
        except Exception:
            return False
        return bool(getattr(result, "success", False))

    def _plugin_data_dir(self) -> Path | None:
        if self._platform is None:
            return None
        try:
            return Path(self._platform.plugin_data_dir())
        except Exception:
            return None

    def _post_ui(self, fn) -> None:
        self._uiCallback.emit(fn)

    @Slot(object)
    def _run_ui_callback(self, fn: object) -> None:
        if not self._disposed and callable(fn):
            fn()

    def _emit_state_in_ui(self, payload: dict) -> None:
        if not self._disposed:
            self.captureStateUpdated.emit(payload)

    def _emit_rows_in_ui(self, rows: list) -> None:
        if not self._disposed:
            self.captureRowsUpdated.emit(rows)

    def _emit_stats_in_ui(self, stats: dict) -> None:
        if not self._disposed:
            self.captureStatsUpdated.emit(stats)

    def _export_sessions(self, flow_ids: list[str], save_path: str, export_format: str) -> None:
        if not save_path:
            self.captureActionResult.emit(False, "未提供导出路径")
            return
        if self._service is None:
            self.captureActionResult.emit(False, "HTTP 抓包服务不可用")
            return
        target = _path_from_qml(save_path)
        ok, message = self._service.export_rows(flow_ids, target, export_format)
        self.captureActionResult.emit(ok, message)


def _path_from_qml(value: str) -> Path:
    if value.startswith("file:"):
        local = QUrl(value).toLocalFile()
        return Path(local)
    return Path(value)


def _format_from_path(value: str) -> str:
    suffix = _path_from_qml(value).suffix.lower()
    return "har" if suffix == ".har" else "json"
