from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any
from uuid import uuid4


_log_context: ContextVar[dict[str, Any]] = ContextVar("suishou_log_context", default={})


@contextmanager
def bind_context(**fields: Any):
    current = dict(_log_context.get())
    current.update({key: value for key, value in fields.items() if value is not None and value != ""})
    token = _log_context.set(current)
    try:
        yield current
    finally:
        _log_context.reset(token)


def get_context() -> dict[str, Any]:
    return dict(_log_context.get())


def make_trace_id() -> str:
    return f"tr_{uuid4().hex[:12]}"


def make_session_id() -> str:
    return f"ps_{uuid4().hex[:12]}"


def make_request_id() -> str:
    return f"rq_{uuid4().hex[:12]}"


def make_task_id() -> str:
    return f"task_{uuid4().hex[:12]}"
