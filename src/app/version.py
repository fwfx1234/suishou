from __future__ import annotations

from importlib import metadata


def get_app_version() -> str:
    try:
        return metadata.version("py-desktop-tools")
    except Exception:
        return "1.0.0"
