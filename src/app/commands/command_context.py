from __future__ import annotations

import re

from app.commands.context import LauncherContext
from app.plugins.manifest import ContextMatcher


class CommandContextMatcher:
    """Applies context-aware boosts and determines launch input policy."""

    @staticmethod
    def normalize_tokens(tokens: list[str]) -> set[str]:
        return {str(token).strip().lower() for token in tokens if str(token).strip()}

    @staticmethod
    def apply_context(
        base_score: int,
        context: LauncherContext,
        prefixes: list[str],
        matchers: list[ContextMatcher] | list[object],
    ) -> tuple[int, list[str]]:
        score = base_score
        reasons: list[str] = []

        normalized_prefixes = CommandContextMatcher.normalize_tokens(prefixes)
        if context.prefix and context.prefix in normalized_prefixes:
            score += 240
            reasons.append(f"prefix:{context.prefix}")

        has_explicit_text = bool(context.input_body.strip() if context.prefix else context.input_text.strip())
        for matcher in matchers:
            source = str(getattr(matcher, "source", "")).strip().lower()
            kind = str(getattr(matcher, "kind", "")).strip().lower()
            boost = int(getattr(matcher, "boost", 0) or 0)
            pattern = str(getattr(matcher, "pattern", "") or "")
            if not source or not kind:
                continue

            if source == "input":
                haystack = context.input_body if context.prefix else context.input_text
                kinds = context.detected_input_kinds
            elif source == "clipboard":
                if has_explicit_text and base_score <= 0 and not (
                    context.prefix and context.prefix in normalized_prefixes
                ):
                    continue
                haystack = context.clipboard_text or context.clipboard_preview
                kinds = context.detected_clipboard_kinds
            else:
                continue

            if CommandContextMatcher._hits(kind, pattern, kinds, haystack):
                score += boost
                reasons.append(f"{source}:{kind}")

        return score, reasons

    @staticmethod
    def launch_input_policy(
        base_score: int,
        context: LauncherContext,
        prefixes: list[str],
        reasons: list[str],
    ) -> tuple[str, str, bool]:
        has_query = bool(context.input_text.strip())
        normalized_prefixes = CommandContextMatcher.normalize_tokens(prefixes)
        prefix_hit = bool(context.prefix and context.prefix in normalized_prefixes)
        input_match = any(reason.startswith("input:") for reason in reasons)

        if prefix_hit:
            return "", "command", has_query
        if input_match and base_score <= 0:
            return context.input_text, "content", has_query
        return "", "command", has_query

    @staticmethod
    def _hits(
        kind: str,
        pattern: str,
        detected_kinds: frozenset[str],
        haystack: str,
    ) -> bool:
        if kind == "regex":
            if not pattern:
                return False
            try:
                return re.search(pattern, haystack, re.IGNORECASE) is not None
            except re.error:
                return pattern.lower() in haystack.lower()
        return kind in detected_kinds
