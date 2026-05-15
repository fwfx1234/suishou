from __future__ import annotations

from enum import StrEnum
from typing import Literal

from app.plugins.manifest import LaunchMode


PluginHost = Literal["inline", "list", "window"]


class PluginSessionState(StrEnum):
    ACTIVE_INLINE = "active_inline"
    ACTIVE_LIST = "active_list"
    ACTIVE_WINDOW = "active_window"
    RETAINED_INLINE = "retained_inline"
    RETAINED_LIST = "retained_list"
    RETAINED_WINDOW = "retained_window"

    @property
    def host(self) -> PluginHost:
        if self.value.endswith("window"):
            return "window"
        if self.value.endswith("list"):
            return "list"
        return "inline"

    @property
    def retained(self) -> bool:
        return self.value.startswith("retained_")


def active_state(
    launch_mode: LaunchMode,
    preferred_host: PluginHost | None = None,
) -> PluginSessionState:
    if preferred_host == "window":
        return PluginSessionState.ACTIVE_WINDOW
    if preferred_host == "list" or launch_mode == "list":
        return PluginSessionState.ACTIVE_LIST
    if preferred_host == "inline" or launch_mode == "inline_view":
        return PluginSessionState.ACTIVE_INLINE
    return PluginSessionState.ACTIVE_WINDOW


def retained_state(launch_mode: LaunchMode, host: PluginHost) -> PluginSessionState:
    if host == "window":
        return PluginSessionState.RETAINED_WINDOW
    if host == "list" or launch_mode == "list":
        return PluginSessionState.RETAINED_LIST
    return PluginSessionState.RETAINED_INLINE


def reactivate_state(
    current: PluginSessionState,
    launch_mode: LaunchMode,
    preferred_host: PluginHost | None = None,
) -> PluginSessionState:
    if preferred_host is not None:
        return active_state(launch_mode, preferred_host)
    if current.host == "window":
        return PluginSessionState.ACTIVE_WINDOW
    if current.host == "list":
        return PluginSessionState.ACTIVE_LIST
    return active_state(launch_mode, None)
