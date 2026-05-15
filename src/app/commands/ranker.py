from __future__ import annotations

from difflib import SequenceMatcher

from app.commands.command_index_db import compute_pinyin


class CommandRanker:
    """Scoring logic for commands, apps, and system items against a query."""

    @staticmethod
    def score(query: str, title: str, keywords: list[str], description: str) -> tuple[int, int, int]:
        """Return (score, highlightStart, highlightLen) for a single item.

        Score ranges: exact match=100, prefix=90, substring=70, keyword=85-55,
        pinyin=54-74, fuzzy=0-50, description=20, no match=0.
        """
        q = query.strip().lower()
        if not q:
            return 1, -1, 0

        title_lower = title.lower()
        if q == title_lower:
            return 100, 0, len(query)
        if title_lower.startswith(q):
            return 90, 0, len(query)
        pos = title_lower.find(q)
        if pos >= 0:
            return 70, pos, len(query)

        for keyword in keywords:
            keyword_lower = str(keyword).lower()
            if q == keyword_lower:
                return 85, -1, 0
            if keyword_lower.startswith(q):
                return 75, -1, 0
            if q in keyword_lower:
                return 55, -1, 0

        pinyin, initials = compute_pinyin(title)
        if pinyin.startswith(q):
            return 74, -1, 0
        if q in pinyin:
            return 54, -1, 0
        if initials.startswith(q):
            return 72, -1, 0

        ratio = SequenceMatcher(None, q, title_lower).ratio()
        if ratio > 0.62:
            return int(ratio * 50), -1, 0
        if q in description.lower():
            return 20, -1, 0
        return 0, -1, 0
