from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


_SENSITIVE_KEYS = {
    "authorization",
    "authvalue",
    "cookie",
    "cookies",
    "set-cookie",
    "password",
    "secret",
    "token",
    "apikey",
    "api-key",
    "x-api-key",
}


def redact_value(key: str, value: Any, *, max_text_length: int = 240) -> Any:
    if _is_sensitive_key(key):
        return "***"
    if isinstance(value, Mapping):
        return {str(inner_key): redact_value(str(inner_key), inner_value, max_text_length=max_text_length) for inner_key, inner_value in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [redact_value(key, item, max_text_length=max_text_length) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, str):
        return _truncate(value, max_text_length)
    return value


def redact_mapping(data: Mapping[str, Any] | None, *, max_text_length: int = 240) -> dict[str, Any]:
    if not data:
        return {}
    return {
        str(key): redact_value(str(key), value, max_text_length=max_text_length)
        for key, value in data.items()
    }


def preview_text(text: str, *, limit: int = 240) -> str:
    value = " ".join((text or "").replace("\r", " ").replace("\n", " ").split())
    if len(value) <= limit:
        return value
    return f"{value[: limit - 3]}..."


def _truncate(text: str, limit: int) -> str:
    value = text or ""
    if len(value) <= limit:
        return value
    return f"{value[: limit - 3]}..."


def _is_sensitive_key(key: str) -> bool:
    normalized = key.replace("_", "-").lower()
    return any(marker in normalized for marker in _SENSITIVE_KEYS)
