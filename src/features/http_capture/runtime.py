from __future__ import annotations

from app.plugins.runtime import SimpleQmlRuntime

from .view_model import HttpCaptureViewModel


def create_runtime() -> SimpleQmlRuntime:
    return SimpleQmlRuntime(lambda ctx: HttpCaptureViewModel(platform_api=ctx.platform))
