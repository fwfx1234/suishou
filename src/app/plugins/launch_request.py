from __future__ import annotations

from dataclasses import dataclass, field

from app.plugins.session_state import PluginHost


@dataclass(frozen=True, slots=True)
class PluginLaunchRequest:
    plugin_id: str
    command_id: str = ""
    input_text: str = ""
    payload: dict = field(default_factory=dict)
    preferred_host: PluginHost | None = None

